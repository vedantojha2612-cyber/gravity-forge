import math
import unittest
import numpy as np

from gravityforge.core.engine import (
    Body,
    GravityEngine,
    G_SI,
    SOLAR_MASS_KG,
    AU_METERS,
    DAY_SECONDS,
    compute_jacobi_constant,
)
from gravityforge.core.fast_engine import FastGravityEngine
from gravityforge.ephemeris.jpl import load_system


class TestConservationLaws(unittest.TestCase):
    """Rigorous tests for fundamental physics conservation laws & numerical stability."""

    def test_symplectic_energy_drift_bound_hourly(self):
        """Verifies symplectic leapfrog keeps relative energy drift < 1e-10 over 8,760 hourly steps."""
        bodies = load_system(["sun", "earth", "jupiter"])
        engine = GravityEngine(bodies, integrator="leapfrog", softening=1e4)

        for _ in range(8760):  # 1 full year
            engine.step(3600.0)

        drift = engine.energy_relative_drift()
        self.assertLess(
            drift,
            1e-10,
            f"Symplectic hourly energy drift exceeded bound: {drift:.3e} > 1e-10",
        )

    def test_symplectic_energy_drift_bound_long_epoch(self):
        """Verifies symplectic leapfrog maintains bounded drift < 1e-7 over 2,000 multi-hour steps."""
        bodies = load_system(["sun", "earth", "jupiter"])
        engine = GravityEngine(bodies, integrator="leapfrog", softening=1e4)

        dt = 3600.0 * 6.0  # 6 hours per step
        for _ in range(2000):  # 500 simulated days
            engine.step(dt)

        drift = engine.energy_relative_drift()
        self.assertLess(
            drift,
            1e-7,
            f"Symplectic 6h energy drift exceeded bound: {drift:.3e} > 1e-7",
        )

    def test_linear_momentum_conservation(self):
        """Newton's 3rd Law requires total linear momentum P_tot to remain constant."""
        bodies = load_system(["sun", "earth", "mars", "jupiter"])
        engine = GravityEngine(bodies, integrator="leapfrog", softening=1e4)

        dt = DAY_SECONDS
        for _ in range(365):
            engine.step(dt)

        p_drift, _ = engine.momentum_relative_drift()
        self.assertLess(
            p_drift,
            1e-12,
            f"Total linear momentum drift exceeded bound: {p_drift:.3e} > 1e-12",
        )

    def test_angular_momentum_conservation(self):
        """No external torque implies total angular momentum L_tot is conserved."""
        bodies = load_system(["sun", "earth", "mars", "jupiter"])
        engine = GravityEngine(bodies, integrator="leapfrog", softening=1e4)

        dt = DAY_SECONDS
        for _ in range(365):
            engine.step(dt)

        _, l_drift = engine.momentum_relative_drift()
        self.assertLess(
            l_drift,
            1e-12,
            f"Total angular momentum drift exceeded bound: {l_drift:.3e} > 1e-12",
        )

    def test_symplectic_time_reversibility(self):
        """Symplectic integrators are time-reversible: S(-dt)^N o S(dt)^N = Identity."""
        bodies = load_system(["sun", "earth", "jupiter"])
        engine = GravityEngine(bodies, integrator="leapfrog", softening=1e4)

        initial_positions = engine.positions.copy()
        initial_velocities = engine.velocities.copy()

        steps = 500
        dt = 3600.0 * 4.0  # 4 hours

        # Forward integration
        for _ in range(steps):
            engine.step(dt)

        # Reverse velocity vectors
        engine.velocities = -engine.velocities

        # Integrate forward in time with reversed velocities
        for _ in range(steps):
            engine.step(dt)

        # Reverse velocities back to compare with initial state
        engine.velocities = -engine.velocities

        pos_error = np.max(np.abs(engine.positions - initial_positions)) / AU_METERS
        vel_error = np.max(np.abs(engine.velocities - initial_velocities))

        self.assertLess(
            pos_error,
            1e-11,
            f"Time reversibility violated in position: {pos_error:.3e} AU > 1e-11 AU",
        )
        self.assertLess(
            vel_error,
            1e-7,
            f"Time reversibility violated in velocity: {vel_error:.3e} m/s > 1e-7 m/s",
        )

    def test_jacobi_constant_constancy_cr3bp(self):
        """Jacobi Constant C_J must remain invariant for a test particle in CR3BP."""
        m_sun = SOLAR_MASS_KG
        m_earth = 5.972e24
        d = AU_METERS

        # Sun and Earth on circular orbits around barycenter
        mu = G_SI * (m_sun + m_earth)
        omega = math.sqrt(mu / (d**3))

        r_cm = (m_earth * d) / (m_sun + m_earth)
        r_sun = np.array([-r_cm, 0.0, 0.0])
        r_earth = np.array([d - r_cm, 0.0, 0.0])

        v_sun = np.array([0.0, -omega * r_cm, 0.0])
        v_earth = np.array([0.0, omega * (d - r_cm), 0.0])

        # Test mass at Sun-Earth L4 Lagrange point (equilateral triangle)
        r_l4 = np.array([0.5 * d - r_cm, (math.sqrt(3) / 2.0) * d, 0.0])
        # L4 corotates with angular velocity omega: v = omega x r
        v_l4 = np.array([-omega * r_l4[1], omega * r_l4[0], 0.0])

        c_j_0 = compute_jacobi_constant(m_sun, m_earth, r_sun, r_earth, r_l4, v_l4)

        # Perturb test particle slightly and check Jacobi constant
        bodies = [
            Body("Sun", m_sun, r_sun, v_sun),
            Body("Earth", m_earth, r_earth, v_earth),
            Body("Satellite", 1000.0, r_l4, v_l4),
        ]
        engine = GravityEngine(bodies, integrator="rk4", softening=1e2)

        dt = 3600.0 * 2.0
        c_j_history = []
        for _ in range(120):  # 10 days
            engine.step(dt)
            cj = compute_jacobi_constant(
                m_sun,
                m_earth,
                engine.positions[0],
                engine.positions[1],
                engine.positions[2],
                engine.velocities[2],
            )
            c_j_history.append(cj)

        c_j_max_drift = max(abs((c - c_j_0) / c_j_0) for c in c_j_history)
        self.assertLess(
            c_j_max_drift,
            1e-5,
            f"Jacobi Constant drift exceeded tolerance: {c_j_max_drift:.3e} > 1e-5",
        )

    def test_fast_engine_equivalence(self):
        """FastGravityEngine preallocated buffers must produce exact numerical parity."""
        bodies_std = load_system(["sun", "earth", "jupiter"])
        bodies_fast = load_system(["sun", "earth", "jupiter"])

        engine_std = GravityEngine(bodies_std, integrator="leapfrog", softening=1e3)
        engine_fast = FastGravityEngine(bodies_fast, integrator="leapfrog", softening=1e3)

        dt = DAY_SECONDS
        for _ in range(100):
            engine_std.step(dt)
            engine_fast.step(dt)

        max_pos_diff = np.max(np.abs(engine_std.positions - engine_fast.positions))
        max_vel_diff = np.max(np.abs(engine_std.velocities - engine_fast.velocities))

        self.assertEqual(
            max_pos_diff,
            0.0,
            f"Discrepancy detected between standard and fast engine positions: {max_pos_diff}",
        )
        self.assertEqual(
            max_vel_diff,
            0.0,
            f"Discrepancy detected between standard and fast engine velocities: {max_vel_diff}",
        )


if __name__ == "__main__":
    unittest.main()
