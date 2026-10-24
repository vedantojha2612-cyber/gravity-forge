"""
GravityForge CLI: Unified command-line interface for the GravityForge engine.
"""
import argparse
import http.server
import os
import socketserver
import subprocess
import sys
import webbrowser

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def run_web(port=8080, open_browser=True):
    web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "web"))
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=web_dir, **kwargs)

    try:
        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            url = f"http://localhost:{port}"
            print(f"🪐 GravityForge 3D WebGL Server running at {url}")
            print("Press Ctrl+C to stop.")
            if open_browser:
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server.")


def run_tui(steps=60, delay=0.03):
    from tui.hud import run_demo_hud
    run_demo_hud(steps=steps, delay_sec=delay)


def run_benchmark(quick=False):
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "demo_step3.py")]
    if quick:
        cmd.append("--quick")
    subprocess.run(cmd)


def run_tests():
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    subprocess.run(cmd, cwd=os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(
        description="🪐 GravityForge: High-Performance Symplectic N-Body & Slingshot Trajectory Engine"
    )
    parser.add_argument(
        "--web", action="store_true", help="Launch the 3D WebGL Spatial Orbit HUD in browser"
    )
    parser.add_argument(
        "--tui", action="store_true", help="Launch real-time 24-bit ANSI/Braille Terminal HUD"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run the high-concurrency performance benchmark suite"
    )
    parser.add_argument(
        "--test", "--audit", action="store_true", help="Run the full 20/20 test & security audit suite"
    )
    parser.add_argument("--port", type=int, default=8080, help="Port for web server (default: 8080)")
    parser.add_argument(
        "--steps", type=int, default=60, help="Number of steps for TUI simulation (default: 60)"
    )

    args = parser.parse_args()

    if args.web:
        run_web(port=args.port)
    elif args.tui:
        run_tui(steps=args.steps)
    elif args.benchmark:
        run_benchmark()
    elif args.test:
        run_tests()
    else:
        print("🪐 GravityForge: High-Performance Symplectic N-Body & Orbital Mechanics Engine")
        print("Options: --web, --tui, --benchmark, --test\nLaunching default Terminal HUD preview...\n")
        run_tui(steps=25)


if __name__ == "__main__":
    main()
