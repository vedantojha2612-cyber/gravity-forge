"""Step 1 Verification Demo: GravityForge Mathematical Physics Core."""

import numpy as np
from gravityforge.core.engine import Body, GravityEngine, G_SI, AU_METERS, SOLAR_MASS_KG, DAY_SECONDS
from gravityforge.ephemeris.jpl import load_system, PLANETARY_METADATA
from gravityforge.orbital.elements import cartesian_to_keplerian


def test_keplerian_conversion():
    print("\n--- 1. Testing Keplerian Orbital Elements ---")
    # Earth around Sun
    mu = G_SI * (PLANETARY_METADATA["sun"]["mass"] + PLANETARY_METADATA["earth"]["mass"])
    r_earth = np.array([AU_METERS, 0.0, 0.0])
    v_circ = np.sqrt(mu / AU_METERS)
    v_earth = np.array([0.0, v_circ, 0.0])

    elem = cartesian_to_keplerian(r_earth, v_earth, mu)
    print(f"Semi-Major Axis: {elem.semi_major_axis / AU_METERS:.4f} AU (Expected: 1.0000 AU)")
    print(f"Eccentricity:     {elem.eccentricity:.6f} (Expected: ~0.0000 circular)")
    print(f"Period:           {elem.orbital_period / DAY_SECONDS:.2f} days (Expected: ~365.25 days)")
    assert abs(elem.semi_major_axis / AU_METERS - 1.0) < 1e-4, "Semi-major axis mismatch"
    assert elem.eccentricity < 1e-4, "Eccentricity mismatch"
    print(" Keplerian Conversion: PASSED")


def test_energy_conservation():
    print("\n--- 2. Testing Symplectic Leapfrog Energy Conservation ---")
    bodies = load_system(["Sun", "Earth", "Jupiter"], use_live_api=False)
    sim = GravityEngine(bodies, integrator="leapfrog", softening=1e3)

    initial_energy = sim.initial_energy
    # Simulate 365 days in 1-hour steps
    dt = 3600.0
    steps = 365 * 24

    for _ in range(steps):
        sim.step(dt)

    rel_drift = sim.energy_relative_drift()
    print(f"Simulated {steps} steps (1 year).")
    print(f"Initial Energy:     {initial_energy:.6e} J")
    print(f"Final Energy:       {sim.current_energy()[2]:.6e} J")
    print(f"Relative Drift:     {rel_drift:.2e}")
    assert rel_drift < 1e-5, f"Energy drift {rel_drift} too high for symplectic integrator!"
    print(" Symplectic Energy Conservation: PASSED (Zero secular energy decay)")


def test_slingshot_maneuver():
    print("\n--- 3. Testing Gravitational Slingshot (Jupiter Flyby) ---")
    m_jupiter = PLANETARY_METADATA["jupiter"]["mass"]
    # Jupiter moving along +X at 13 km/s
    jupiter = Body(
        name="Jupiter",
        mass=m_jupiter,
        position=np.array([0.0, 0.0, 0.0]),
        velocity=np.array([13000.0, 0.0, 0.0]),
    )
    # Probe approaching Jupiter from behind along -Y and +X to swing around Jupiter's trailing side
    probe = Body(
        name="VoyagerProbe",
        mass=800.0,
        position=np.array([-5.0e8, -1.0e9, 0.0]),
        velocity=np.array([8000.0, 14000.0, 0.0]),
    )

    sim = GravityEngine([jupiter, probe], integrator="rk4", softening=100.0)
    v0_probe = np.linalg.norm(sim.bodies[1].velocity)

    # 100,000 seconds with dt = 25s (~1.15 days, flyby duration)
    dt = 25.0
    for _ in range(4000):
        sim.step(dt)

    v_final_probe = np.linalg.norm(sim.bodies[1].velocity)
    delta_v = v_final_probe - v0_probe
    print(f"Probe initial speed (heliocentric frame): {v0_probe:.2f} m/s")
    print(f"Probe final speed   (heliocentric frame): {v_final_probe:.2f} m/s")
    print(f"Gravity Assist Boost Delta-V:           +{delta_v:.2f} m/s")
    assert delta_v > 1000.0, "Gravity assist boost failed"
    print(" Slingshot Flyby Trajectory: PASSED")


if __name__ == "__main__":
    test_keplerian_conversion()
    test_energy_conservation()
    test_slingshot_maneuver()
    print("\n ALL STEP 1 CORE PHYSICS TESTS PASSED VERIFIED")
