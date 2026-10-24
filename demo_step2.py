"""
GravityForge Step 2 Demo: Dual-Interface Visualizer
Runs either the ANSI/Braille Terminal HUD or opens the 3D WebGL Three.js Canvas.
"""

import argparse
import os
import sys
import webbrowser

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def main():
    parser = argparse.ArgumentParser(description="GravityForge Step 2 Visualizer Demo")
    parser.add_argument(
        "--mode",
        choices=["tui", "web", "both"],
        default="tui",
        help="Display mode: 'tui' for terminal HUD, 'web' for 3D Three.js canvas, 'both' for both.",
    )
    parser.add_argument("--steps", type=int, default=30, help="Number of steps to animate in TUI mode.")
    args = parser.parse_args()

    web_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "web", "index.html"))

    if args.mode in ("web", "both"):
        print(f"Opening 3D WebGL Canvas: file://{web_path}")
        try:
            webbrowser.open(f"file://{web_path}")
        except Exception as e:
            print(f"Could not open default browser: {e}")

    if args.mode in ("tui", "both"):
        from tui.hud import run_demo_hud
        run_demo_hud(steps=args.steps, delay_sec=0.03)


if __name__ == "__main__":
    main()
