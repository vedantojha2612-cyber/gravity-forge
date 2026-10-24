"""
GravityForge Live Terminal HUD (TUI)
ANSI & Braille Trajectory Plotter & Ephemeris Telemetry Monitor
"""

import math
import os
import sys
import time
from typing import List, Tuple

# Ensure gravityforge package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gravityforge.core.engine import Body, GravityEngine, AU_METERS, DAY_SECONDS, G_SI
from gravityforge.ephemeris.jpl import load_system

# ANSI Color Codes & Styles
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[38;2;0;240;255m"
AMBER = "\033[38;2;255;184;0m"
CRIMSON = "\033[38;2;255;0;60m"
GREEN = "\033[38;2;0;255;136m"
PURPLE = "\033[38;2;180;100;255m"
GRAY = "\033[38;2;120;140;160m"
DARK_GRAY = "\033[38;2;45;55;72m"


def hex_to_ansi(hex_str: str) -> str:
    """Converts a hex color (#RRGGBB) to 24-bit ANSI truecolor escape sequence."""
    if not hex_str:
        return DARK_GRAY
    if hex_str.startswith("\033"):
        return hex_str
    clean = hex_str.lstrip("#")
    if len(clean) == 6:
        try:
            r = int(clean[0:2], 16)
            g = int(clean[2:4], 16)
            b = int(clean[4:6], 16)
            return f"\033[38;2;{r};{g};{b}m"
        except ValueError:
            pass
    return CYAN


class BrailleCanvas:
    """High-resolution 2D terminal canvas utilizing 2x4 Unicode Braille dot patterns."""

    def __init__(self, cols: int = 58, rows: int = 22):
        self.cols = cols
        self.rows = rows
        self.pixel_width = cols * 2
        self.pixel_height = rows * 4
        self.grid = [[0 for _ in range(self.pixel_width)] for _ in range(self.pixel_height)]
        self.color_grid = [[None for _ in range(cols)] for _ in range(rows)]

    def clear(self):
        for r in range(self.pixel_height):
            for c in range(self.pixel_width):
                self.grid[r][c] = 0
        for r in range(self.rows):
            for c in range(self.cols):
                self.color_grid[r][c] = None

    def set_pixel(self, x: int, y: int, color: str = CYAN):
        if 0 <= x < self.pixel_width and 0 <= y < self.pixel_height:
            self.grid[y][x] = 1
            cell_x = x // 2
            cell_y = y // 4
            self.color_grid[cell_y][cell_x] = color

    def render_rows(self) -> List[str]:
        output_lines = []
        for r in range(self.rows):
            line = ""
            for c in range(self.cols):
                code = 0
                dot_offsets = [
                    (0, 0, 0x01),
                    (0, 1, 0x02),
                    (0, 2, 0x04),
                    (1, 0, 0x08),
                    (1, 1, 0x10),
                    (1, 2, 0x20),
                    (0, 3, 0x40),
                    (1, 3, 0x80),
                ]
                for dx, dy, bit in dot_offsets:
                    px = c * 2 + dx
                    py = r * 4 + dy
                    if 0 <= py < self.pixel_height and 0 <= px < self.pixel_width:
                        if self.grid[py][px]:
                            code |= bit

                char = chr(0x2800 + code) if code > 0 else " "
                ansi_col = hex_to_ansi(self.color_grid[r][c]) if self.color_grid[r][c] else DARK_GRAY
                line += f"{ansi_col}{char}{RESET}"
            output_lines.append(line)
        return output_lines


def render_hud_frame(
    engine: GravityEngine,
    canvas: BrailleCanvas,
    step_num: int,
    scale_au: float = 1.8,
    trail_buffer: List[Tuple[float, float, str]] = None,
) -> str:
    """Builds and returns a complete, formatted HUD snapshot string."""
    canvas.clear()
    pw = canvas.pixel_width
    ph = canvas.pixel_height
    cx = pw // 2
    cy = ph // 2

    # Draw coordinate axes center cross with subtle dim dots
    for x in range(0, pw, 6):
        canvas.set_pixel(x, cy, DARK_GRAY)
    for y in range(0, ph, 6):
        canvas.set_pixel(cx, y, DARK_GRAY)

    # Plot historical trajectory trails
    if trail_buffer:
        for tx, ty, tcolor in trail_buffer:
            px = int(cx + (tx / (scale_au * AU_METERS)) * (pw / 2.2))
            py = int(cy - (ty / (scale_au * AU_METERS)) * (ph / 2.2))
            canvas.set_pixel(px, py, tcolor)

    # Plot current celestial body positions
    for i, body in enumerate(engine.bodies):
        pos = engine.positions[i]
        px = int(cx + (pos[0] / (scale_au * AU_METERS)) * (pw / 2.2))
        py = int(cy - (pos[1] / (scale_au * AU_METERS)) * (ph / 2.2))
        canvas.set_pixel(px, py, body.color)

    braille_lines = canvas.render_rows()

    # Telemetry metrics
    e_kin, e_pot, e_tot = engine.current_energy()
    drift = engine.energy_relative_drift()
    drift_color = GREEN if drift < 1e-6 else (AMBER if drift < 1e-3 else CRIMSON)
    days_elapsed = engine.time / DAY_SECONDS

    # Header Box
    lines = []
    lines.append(f"{BOLD}{CYAN}╔════════════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    lines.append(f"{BOLD}{CYAN}║  {GREEN}●{CYAN} GRAVITYFORGE // N-BODY ORBITAL MECHANICS & TRAJECTORY HUD       STEP: {step_num:06d}                 ║{RESET}")
    lines.append(f"{BOLD}{CYAN}║  INTEGRATOR: {engine.integrator.upper():<10}  EPOCH: T+{days_elapsed:8.2f} DAYS        CONSERVATION: {drift_color}{drift:10.3e} ΔE/E₀{CYAN}  ║{RESET}")
    lines.append(f"{BOLD}{CYAN}╚════════════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")

    # Main split pane: Trajectory Canvas Left | Telemetry Right
    lines.append(f"{BOLD}{CYAN}┌─ [ ORBITAL PROJECTION (FOV: {scale_au*2:.1f} AU) ] ───────┐ ┌─ [ ENERGY & SYSTEM TELEMETRY ] ──────────┐{RESET}")

    side_panel_items = [
        f"Kinetic E  : {e_kin:13.6e} J",
        f"Potential E: {e_pot:13.6e} J",
        f"Total E    : {e_tot:13.6e} J",
        f"Energy Drift: {drift_color}{drift:13.6e}{RESET}",
        f"G Constant : {G_SI:.5e} SI",
        "────────────────────────────────────────",
        f"Active Bodies: {len(engine.bodies):<4}",
    ]

    for i in range(len(braille_lines)):
        left = f"│{braille_lines[i]}│"
        if i < len(side_panel_items):
            right = f"│ {side_panel_items[i]:<38} │"
        elif i == len(side_panel_items):
            right = f"│ {BOLD}{CYAN}CELESTIAL EPHEMERIS SUMMARY:{RESET}             │"
        elif i - (len(side_panel_items) + 1) < len(engine.bodies):
            b_idx = i - (len(side_panel_items) + 1)
            b = engine.bodies[b_idx]
            pos = engine.positions[b_idx]
            vel = engine.velocities[b_idx]
            dist_au = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2) / AU_METERS
            speed_kms = math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2) / 1000.0
            entry = f"• {b.name[:7]:<7}: {dist_au:4.2f}AU {speed_kms:5.1f}km/s"
            right = f"│ {entry:<38} │"
        else:
            right = f"│{' ' * 38}│"
        lines.append(f"{left} {right}")

    lines.append(f"{BOLD}{CYAN}└──────────────────────────────────────────────────────────┘ └────────────────────────────────────────┘{RESET}")
    return "\n".join(lines)


def run_demo_hud(steps: int = 40, delay_sec: float = 0.02):
    """Runs a live animated demonstration of the terminal HUD."""
    bodies = load_system(["sun", "mercury", "venus", "earth", "mars"])
    engine = GravityEngine(bodies, integrator="leapfrog")
    canvas = BrailleCanvas(cols=58, rows=22)
    trail_buffer: List[Tuple[float, float, str]] = []

    dt = 86400.0 * 2.0  # 2 days per step
    for step in range(steps):
        engine.step(dt)

        for i, b in enumerate(engine.bodies):
            if b.name.lower() != "sun":
                trail_buffer.append((engine.positions[i][0], engine.positions[i][1], b.color))
        if len(trail_buffer) > 400:
            trail_buffer = trail_buffer[-400:]

        hud_output = render_hud_frame(
            engine=engine,
            canvas=canvas,
            step_num=step + 1,
            scale_au=1.8,
            trail_buffer=trail_buffer,
        )

        if step == steps - 1 or step % 10 == 0:
            print("\033[H\033[J" + hud_output, flush=True)
            time.sleep(delay_sec)


if __name__ == "__main__":
    run_demo_hud(steps=15, delay_sec=0.01)
