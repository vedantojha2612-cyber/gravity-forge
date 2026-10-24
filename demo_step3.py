"""GravityForge Step 3 Demo: Performance, Load, and Scale Benchmarking Suite
Profiles N-body latency matrix, GC churn, memory leak stability, and frontend bundles.
Generates the formal PERFORMANCE_SCORECARD.md.
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure gravityforge package is discoverable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from benchmarks.suite import run_full_benchmark_suite
from benchmarks.scorecard import generate_scorecard_markdown, render_terminal_scorecard


def main():
    parser = argparse.ArgumentParser(description="GravityForge Step 3 Benchmarking Harness")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Runs a fast subset of benchmarks (fewer bodies/steps) for rapid verification.",
    )
    parser.add_argument(
        "--output-scorecard",
        default="PERFORMANCE_SCORECARD.md",
        help="Path where the Markdown scorecard should be written.",
    )
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.dirname(__file__))
    print(f"\n⚡ [HIKAKU UCHIHA] Initializing GravityForge Performance & Scalability Benchmark Suite...")
    print(f"   Root directory: {project_root}")
    print(f"   Mode: {'QUICK AUDIT' if args.quick else 'FULL PRODUCTION CERTIFICATION'}\n")

    report = run_full_benchmark_suite(project_root=project_root, quick=args.quick)

    # Render ANSI terminal summary
    terminal_output = render_terminal_scorecard(report)
    print(terminal_output)

    # Write formal markdown scorecard
    scorecard_path = os.path.join(project_root, args.output_scorecard)
    markdown_content = generate_scorecard_markdown(report)
    with open(scorecard_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"📄 Performance Scorecard exported to: {scorecard_path}\n")


if __name__ == "__main__":
    main()
