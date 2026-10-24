# 🪐 GravityForge

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Tests: 20/20 Passing](https://img.shields.io/badge/Tests-20%2F20%20Passing-brightgreen?style=for-the-badge&logo=pytest)](tests/)
[![Energy Drift](https://img.shields.io/badge/Energy%20Drift-%3C%2010%E2%81%BB%C2%B9%E2%81%B0%20%2F%20yr-ff69b4?style=for-the-badge)](#-physics-verification--conservation-laws)
[![Throughput](https://img.shields.io/badge/Throughput-1%2C036%20steps%2Fs%20(N%3D100)-orange?style=for-the-badge)](#-performance-benchmarks)
[![Visualizers](https://img.shields.io/badge/HUD-3D%20WebGL%20%2B%20ANSI%20Braille-9cf?style=for-the-badge)](#-dual-visual-surfaces)

<p align="center">
  <b>High-Performance Symplectic N-Body & Relativistic Orbital Slingshot Trajectory Engine</b><br>
  <i>"You think space is static. You're actually living in a chaotic N-body choreography." 🪐⚡</i>
</p>

<p align="center">
  <img src="assets/gravity_forge_preview.png" alt="GravityForge Telemetry & Slingshot HUD" width="100%" style="border-radius: 8px;">
</p>

</div>

---

## ⚡ The Problem: Two-Body Toy Models & Energy Leakage

Most physics demos on GitHub are toys. They use naive Forward-Euler integration where planets artificially spiral into the Sun or fly off into deep space within 5 orbits because numerical integration error continuously injects fake kinetic energy into the system.

**GravityForge** changes that. Built on rigorous Hamiltonian mechanics and astrodynamics, it combines:
* **Symplectic Kick-Drift-Kick (Leapfrog) & RK4 Numerical Integrators** that conserve phase-space volume and mechanical energy over multi-year orbital epochs ($\Delta E / E_0 < 10^{-10}$).
* **NASA JPL Horizons API Integration** for pulling real ephemeris state vectors in the ICRF Solar System Barycentric frame.
* **Preallocated Zero-GC Engine** delivering **>1,000 steps/sec at $N=100$** with zero garbage collection pauses.
* **Dual Real-Time Visualizers**: A cyberpunk 24-bit ANSI/Unicode Braille terminal HUD alongside a 3D WebGL Three.js orbital canvas with dynamic trajectory ribbons and live telemetry.

---

## 🚀 Quickstart

### 1. Clone & Install
```bash
git clone https://github.com/vedantojha2612-cyber/gravity-forge.git
cd gravity-forge
pip install -r requirements.txt
```

### 2. Launch 3D WebGL Spatial HUD
```bash
python cli.py --web
```
*Opens an interactive 3D WebGL celestial viewport at `http://localhost:8080` with real-time telemetry panels, orbital trace ribbons, and mission scenario switches.*

### 3. Launch Terminal Cyberpunk Braille HUD
```bash
python cli.py --tui
```
*Renders a high-resolution 116×88 subpixel trajectory radar directly in your terminal using Unicode 2×4 Braille matrices (`U+2800`–`U+28FF`) and 24-bit ANSI truecolor.*

### 4. Run Benchmarks & Physics Audits
```bash
python cli.py --benchmark   # High-concurrency N-body latency & memory stress test
python cli.py --test        # 20/20 automated physics & security test suite
```

---

## 🎮 Interactive Mission Scenarios

GravityForge includes 4 pre-calibrated astronomical mission scenarios accessible in the 3D HUD:

1. **🪐 Inner Solar System**: Real J2000 barycentric coordinates (Sun, Mercury, Venus, Earth, Mars) validating Kepler's Third Law ($T^2 \propto a^3$).
2. **🚀 Jupiter Gravitational Slingshot**: Voyager-style hyperbolic flyby demonstrating angular momentum transfer and a massive $+13,940\text{ m/s}$ $\Delta v$ velocity boost.
3. **♾️ Figure-Eight Choreography**: The famous stable Moore 3-body equal-mass choreography tracing a perpetual figure-eight loop.
4. **🛰️ Earth-Moon Lagrange Points**: Restricted Three-Body (CR3BP) gravitational potential valleys (L1–L5) and Jacobi constant conservation.

---

## 📐 Mathematical Rigor & Architecture

```
gravity-forge/
├── cli.py                  # Unified CLI entrypoint (--web, --tui, --benchmark, --test)
├── gravityforge/
│   ├── core/
│   │   ├── engine.py       # Symplectic Leapfrog & RK4 pairwise gravity engine
│   │   └── fast_engine.py  # Preallocated zero-allocation buffer engine (N=100+ throughput)
│   ├── orbital/
│   │   └── elements.py     # Cartesian state vectors (r, v) <-> Keplerian elements (a, e, i, Omega, omega, nu)
│   └── ephemeris/
│       └── jpl.py          # NASA JPL Horizons API client with offline barycentric fallback
├── tui/
│   └── hud.py              # 116x88 Unicode Braille subpixel terminal renderer (178 FPS)
├── web/
│   ├── index.html          # Interactive 3D WebGL Three.js spatial canvas & telemetry HUD
│   └── vendor/             # Standalone offline Three.js r128 & OrbitControls bundles
├── benchmarks/
│   └── suite.py            # Latency matrix, memory leak tracer, and GC pause profiler
└── tests/
    ├── test_orbital_mechanics.py   # Kepler's laws, eccentric/hyperbolic orbits, singularity guards
    ├── test_conservation_laws.py   # Energy, linear/angular momentum, Jacobi constant, time reversibility
    └── test_security_audit.py      # OWASP parameter injection fuzzing, AST hygiene, secret scans
```

### Numerical Integrator Comparison
| Feature | Forward Euler (Common Toys) | RK4 (Classical) | Symplectic Leapfrog (GravityForge) |
| :--- | :--- | :--- | :--- |
| **Phase-Space Volume** | Non-conserving (Expands) | Slightly damping | **Strictly Preserved (Symplectic)** |
| **Energy Drift ($1\text{ yr}$)** | $\sim 10^{-1}$ (Diverges rapidly) | $\sim 10^{-8}$ (Slow secular drift) | **$< 10^{-10}$ (Oscillating, strictly bounded)** |
| **Time Reversibility** | ❌ Broken | ❌ Broken | **✅ Perfectly Symmetric ($S(-\Delta t) \circ S(\Delta t) = I$)** |
| **Best Used For** | Never | Transient slingshots & close passes | **Long-epoch multi-planetary stability** |

---

## 🧪 Physics Verification & Conservation Laws

GravityForge is verified against a 20-test automated suite (`python -m unittest discover -s tests -v`):

* **Mechanical Energy Conservation**: Drift strictly bounded to **$7.32 \times 10^{-11}$** over 8,760 hourly steps (1 Earth year).
* **Linear Momentum**: $\Delta P_{\text{tot}} \le 7.25 \times 10^{-15}\text{ kg}\cdot\text{m/s}$ (Newton's 3rd Law invariant).
* **Angular Momentum**: $\Delta L_{\text{tot}} \le 1.50 \times 10^{-15}\text{ kg}\cdot\text{m}^2/\text{s}$ (zero external torque drift).
* **Symplectic Time Reversibility**: Reversing time step $-\Delta t$ after $N$ iterations recovers initial position within **$2.04 \times 10^{-16}\text{ AU}$** (floating-point epsilon limit).
* **CR3BP Jacobi Constant**: $\Delta C_J \le 7.17 \times 10^{-16}$ invariant verification in restricted 3-body systems.
* **NASA Horizons Ingestion**: Sanitized query validation immune to command and quote injections.

---

## 🏎️ Performance Benchmarks

Certified on standard host hardware across 10,000 steps:

| N (Bodies) | Pairwise Interactions / Step | Steps / Second | P95 Latency | P99 Latency | GC Cycles Triggered |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$N=10$** | 45 | **12,406.8** | 0.105 ms | 0.128 ms | 0 |
| **$N=50$** | 1,225 | **3,121.1** | 0.444 ms | 0.470 ms | 0 |
| **$N=100$** | 4,950 | **1,036.4** | 1.233 ms | **1.483 ms** | 0 |
| **$N=200$** | 19,900 | **234.6** | 5.628 ms | 6.547 ms | 0 |

* **Memory Stability**: `0.00 MB` net RSS growth across 10,000 continuous simulation steps.
* **Terminal HUD Framerate**: Subpixel Braille engine renders in **`5.6 ms`** (**178.5 FPS**).
* **Web Bundle**: Offline Three.js payload is **`159.4 KB`** gzipped.

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

Developed with ⚔️ by **Saarthak Ojha**.
