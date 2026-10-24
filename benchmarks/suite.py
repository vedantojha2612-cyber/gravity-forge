"""GravityForge High-Performance Benchmarking & Profiling Suite.
Measures latency percentiles, throughput scaling, memory stability, GC churn, and frontend budgets.
"""

from __future__ import annotations

import gc
import gzip
import os
import resource
import sys
import time
import tracemalloc
from typing import Any, Dict, List, Tuple
import numpy as np

# Ensure root package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gravityforge.core.engine import Body, GravityEngine
from gravityforge.core.fast_engine import FastGravityEngine


def generate_benchmark_cluster(n: int, seed: int = 42) -> List[Body]:
    """Generates a stable N-body gravitational cluster for deterministic profiling."""
    rng = np.random.default_rng(seed)
    bodies = []

    # Primary massive central body (Sun-like)
    bodies.append(
        Body(
            name="Primary_Star",
            mass=1.989e30,
            position=np.zeros(3, dtype=np.float64),
            velocity=np.zeros(3, dtype=np.float64),
            radius=6.96e8,
            color="#FFD700",
        )
    )

    # N-1 orbiting bodies
    for i in range(1, n):
        radius = rng.uniform(0.3e11, 4.0e11)
        angle = rng.uniform(0, 2 * np.pi)
        z = rng.uniform(-1e9, 1e9)
        pos = np.array([radius * np.cos(angle), radius * np.sin(angle), z], dtype=np.float64)

        # Circular orbital velocity approximation v ~ sqrt(G * M / r)
        v_mag = np.sqrt(6.67430e-11 * 1.989e30 / radius)
        vel = np.array([-v_mag * np.sin(angle), v_mag * np.cos(angle), rng.uniform(-500, 500)], dtype=np.float64)
        mass = rng.uniform(1e22, 1e27)

        bodies.append(
            Body(
                name=f"Body_{i:03d}",
                mass=mass,
                position=pos,
                velocity=vel,
                radius=rng.uniform(1e6, 7e7),
                color="#00F0FF",
            )
        )
    return bodies


def benchmark_scale(
    body_counts: List[int] = [10, 25, 50, 100, 200, 500],
    steps: int = 100,
    dt: float = 60.0,
) -> List[Dict[str, Any]]:
    """Profiles latency and throughput scaling across body counts for both engines."""
    results = []

    for n in body_counts:
        # Standard Engine Profile
        bodies_std = generate_benchmark_cluster(n)
        engine_std = GravityEngine(bodies_std, integrator="leapfrog")
        for _ in range(5):  # Warmup
            engine_std.step(dt)

        latencies_std = []
        t0_std = time.perf_counter()
        for _ in range(steps):
            t_start = time.perf_counter_ns()
            engine_std.step(dt)
            t_end = time.perf_counter_ns()
            latencies_std.append((t_end - t_start) / 1e6)  # ms
        total_time_std = time.perf_counter() - t0_std

        # FastEngine Profile
        bodies_fast = generate_benchmark_cluster(n)
        engine_fast = FastGravityEngine(bodies_fast, integrator="leapfrog")
        for _ in range(5):  # Warmup
            engine_fast.step(dt)

        latencies_fast = []
        t0_fast = time.perf_counter()
        for _ in range(steps):
            t_start = time.perf_counter_ns()
            engine_fast.step(dt)
            t_end = time.perf_counter_ns()
            latencies_fast.append((t_end - t_start) / 1e6)  # ms
        total_time_fast = time.perf_counter() - t0_fast

        arr_std = np.array(latencies_std)
        arr_fast = np.array(latencies_fast)

        results.append({
            "n": n,
            "steps": steps,
            # Standard engine
            "std_throughput": steps / total_time_std,
            "std_mean_ms": float(np.mean(arr_std)),
            "std_p50_ms": float(np.median(arr_std)),
            "std_p95_ms": float(np.percentile(arr_std, 95)),
            "std_p99_ms": float(np.percentile(arr_std, 99)),
            # Fast engine
            "fast_throughput": steps / total_time_fast,
            "fast_mean_ms": float(np.mean(arr_fast)),
            "fast_p50_ms": float(np.median(arr_fast)),
            "fast_p95_ms": float(np.percentile(arr_fast, 95)),
            "fast_p99_ms": float(np.percentile(arr_fast, 99)),
            "speedup": (steps / total_time_fast) / (steps / total_time_std),
        })

    return results


def benchmark_memory_leak(n: int = 100, steps: int = 10000, dt: float = 60.0) -> Dict[str, Any]:
    """Runs a long-horizon stress run (10,000 steps) to detect memory leaks and RSS growth."""
    bodies = generate_benchmark_cluster(n)
    engine = FastGravityEngine(bodies, integrator="leapfrog")

    # Warmup
    for _ in range(10):
        engine.step(dt)

    gc.collect()
    tracemalloc.start()
    snap_start = tracemalloc.take_snapshot()

    def get_rss_mb() -> float:
        # ru_maxrss is in kilobytes on Linux
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    rss_start = get_rss_mb()
    samples = []
    checkpoint_interval = max(1, steps // 5)

    for i in range(1, steps + 1):
        engine.step(dt)
        if i % checkpoint_interval == 0 or i == steps:
            curr_rss = get_rss_mb()
            curr_peak = tracemalloc.get_traced_memory()[1] / (1024.0 * 1024.0)
            samples.append({
                "step": i,
                "rss_mb": curr_rss,
                "tracemalloc_peak_mb": curr_peak,
            })

    snap_end = tracemalloc.take_snapshot()
    top_diffs = snap_end.compare_to(snap_start, "lineno")
    net_allocated_bytes = sum(d.size_diff for d in top_diffs)
    tracemalloc.stop()

    rss_end = get_rss_mb()
    rss_growth_mb = max(0.0, rss_end - rss_start)

    return {
        "n_bodies": n,
        "total_steps": steps,
        "rss_start_mb": rss_start,
        "rss_end_mb": rss_end,
        "rss_growth_mb": rss_growth_mb,
        "net_tracemalloc_kb": net_allocated_bytes / 1024.0,
        "samples": samples,
        "passed": rss_growth_mb < 5.0 and (net_allocated_bytes / 1024.0) < 100.0,
    }


def benchmark_gc_churn(n: int = 100, steps: int = 2000, dt: float = 60.0) -> Dict[str, Any]:
    """Evaluates Python Cyclic Garbage Collector churn and memory churn during intense calculation loops."""
    bodies = generate_benchmark_cluster(n)
    engine = FastGravityEngine(bodies, integrator="leapfrog")

    gc.collect()
    gc_stats_before = [s.copy() for s in gc.get_stats()]
    gc_counts_before = gc.get_count()

    for _ in range(steps):
        engine.step(dt)

    gc_counts_after = gc.get_count()
    gc_stats_after = [s.copy() for s in gc.get_stats()]

    collections_gen0 = gc_stats_after[0]["collections"] - gc_stats_before[0]["collections"]
    collections_gen1 = gc_stats_after[1]["collections"] - gc_stats_before[1]["collections"]
    collections_gen2 = gc.get_stats_after[2]["collections"] - gc_stats_before[2]["collections"]

    return {
        "n_bodies": n,
        "steps": steps,
        "gen0_collections": collections_gen0,
        "gen1_collections": collections_gen1,
        "gen2_collections": collections_gen2,
        "total_gc_collections": collections_gen0 + collections_gen1 + collections_gen2,
        "gc_churn_free": (collections_gen0 + collections_gen1 + collections_gen2) == 0,
    }


def profile_frontend_assets(project_root: str) -> Dict[str, Any]:
    """Profiles web asset bundle sizes, gzip compression ratios, and budget adherence."""
    web_dir = os.path.join(project_root, "web")
    files_to_check = [
        ("index.html", os.path.join(web_dir, "index.html")),
        ("vendor/three.min.js", os.path.join(web_dir, "vendor", "three.min.js")),
        ("vendor/OrbitControls.js", os.path.join(web_dir, "vendor", "OrbitControls.js")),
    ]

    assets = []
    total_raw = 0
    total_gzip = 0

    for name, path in files_to_check:
        if os.path.exists(path):
            with open(path, "rb") as f:
                content = f.read()
            raw_size = len(content)
            gzip_size = len(gzip.compress(content, compresslevel=9))
            ratio = (1.0 - (gzip_size / raw_size)) * 100.0 if raw_size > 0 else 0.0

            total_raw += raw_size
            total_gzip += gzip_size


            assets.append({
                "asset": name,
                "raw_kb": raw_size / 1024.0,
                "gzip_kb": gzip_size / 1024.0,
                "compression_ratio": ratio,
            })

    # Performance Budgets: Total raw < 750 KB, Gzip < 200 KB
    budget_passed = total_raw < (750 * 1024) and total_gzip < (200 * 1024)

    return {
        "assets": assets,
        "total_raw_kb": total_raw / 1024.0,
        "total_gzip_kb": total_gzip / 1024.0,
        "budget_passed": budget_passed,
    }


def profile_terminal_hud(project_root: str, frames: int = 60) -> Dict[str, Any]:
    """Profiles terminal Braille canvas rendering throughput and latency."""
    from tui.hud import BrailleCanvas, render_hud_frame
    from gravityforge.ephemeris.jpl import load_system

    bodies = load_system(["sun", "mercury", "venus", "earth", "mars"])
    engine = FastGravityEngine(bodies, integrator="leapfrog")
    canvas = BrailleCanvas(cols=58, rows=22)

    latencies = []
    trail_buffer = []
    for step in range(frames):
        engine.step(86400.0)
        for i, b in enumerate(engine.bodies):
            if b.name.lower() != "sun":
                trail_buffer.append((engine.positions[i][0], engine.positions[i][1], b.color))
        if len(trail_buffer) > 200:
            trail_buffer = trail_buffer[-200:]


        t_start = time.perf_counter_ns()
        render_hud_frame(engine, canvas, step_num=step + 1, scale_au=1.8, trail_buffer=trail_buffer)
        t_end = time.perf_counter_ns()
        latencies.append((t_end - t_start) / 1e6)

    arr = np.array(latencies)
    mean_ms = float(np.mean(arr))
    p95_ms = float(np.percentile(arr, 95))
    fps = 1000.0 / mean_ms if mean_ms > 0 else 0.0

    return {
        "frames": frames,
        "render_mean_ms": mean_ms,
        "render_p95_ms": p95_ms,
        "render_fps_ceiling": fps,
        "hud_60fps_capable": fps >= 60.0,
    }


def run_full_benchmark_suite(project_root: str, quick: bool = False) -> Dict[str, Any]:
    """Executes the complete GravityForge performance, load, and telemetry benchmark suite."""
    scale_counts = [10, 50, 100] if quick else [10, 25, 50, 100, 200, 500]
    leak_steps = 2000 if quick else 10000

    scale_results = benchmark_scale(body_counts=scale_counts, steps=100)
    leak_result = benchmark_memory_leak(n=100, steps=leak_steps)
    gc_result = benchmark_gc_churn(n=100, steps=2000)
    asset_result = profile_frontend_assets(project_root)
    hud_result = profile_terminal_hud(project_root, frames=50)

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "scale": scale_results,
        "leak": leak_result,
        "gc": gc_result,
        "assets": asset_result,
        "hud": hud_result,
    }
