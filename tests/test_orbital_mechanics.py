import math
import unittest
import numpy as np

from gravityforge.core.engine import G_SI, SOLAR_MASS_KG, AU_METERS
from gravityforge.orbital.elements import cartesian_to_keplerian, KeplerianElements


class TestOrbitalMechanics(unittest.TestCase):
    """Rigorous tests for Keplerian elements calculation and orbital mechanics laws."""

    def setUp(self):
        self.mu_sun = G_SI * SOLAR_MASS_KG

    def test_circular_orbit_earth(self):
        """Earth circular orbit at 1 AU must yield e ~ 0, a ~ 1 AU, T ~ 365.25 days."""
        r = np.array([AU_METERS, 0.0, 0.0])
        # Circular orbital speed: v = sqrt(mu / r)
        v_circ = math.sqrt(self.mu_sun / AU_METERS)
        v = np.array([0.0, v_circ, 0.0])

        elements = cartesian_to_keplerian(r, v, self.mu_sun)

        self.assertAlmostEqual(elements.semi_major_axis / AU_METERS, 1.0, places=4)
        self.assertAlmostEqual(elements.eccentricity, 0.0, places=6)
        self.assertAlmostEqual(elements.inclination, 0.0, places=6)
        period_days = elements.orbital_period / 86400.0
        self.assertAlmostEqual(period_days, 365.25, delta=0.5)

    def test_keplers_third_law_scaling(self):
        """Verifies Kepler's Third Law (T^2 / a^3 = 4 * pi^2 / mu) across varied distances."""
        expected_ratio = (4.0 * (math.pi**2)) / self.mu_sun

        distances_au = [0.387, 0.723, 1.0, 1.524, 5.204, 9.582]  # Mercury to Saturn
        for d_au in distances_au:
            r_val = d_au * AU_METERS
            v_val = math.sqrt(self.mu_sun / r_val)
            r = np.array([r_val, 0.0, 0.0])
            v = np.array([0.0, v_val, 0.0])

            elements = cartesian_to_keplerian(r, v, self.mu_sun)
            ratio = (elements.orbital_period**2) / (elements.semi_major_axis**3)
            self.assertAlmostEqual(ratio, expected_ratio, places=8)

    def test_elliptical_orbit_eccentricity(self):
        """An eccentric orbit (perihelion = 0.5 AU, aphelion = 1.5 AU -> a=1.0 AU, e=0.5)."""
        r_peri = 0.5 * AU_METERS
        a_target = 1.0 * AU_METERS
        e_target = 0.5

        # Speed at perihelion: v = sqrt(mu * (2/r - 1/a))
        v_peri = math.sqrt(self.mu_sun * (2.0 / r_peri - 1.0 / a_target))
        r = np.array([r_peri, 0.0, 0.0])
        v = np.array([0.0, v_peri, 0.0])

        elements = cartesian_to_keplerian(r, v, self.mu_sun)
        self.assertAlmostEqual(elements.semi_major_axis / AU_METERS, 1.0, places=4)
        self.assertAlmostEqual(elements.eccentricity, e_target, places=4)
        self.assertTrue(np.isfinite(elements.orbital_period))

    def test_hyperbolic_escape_orbit(self):
        """Hyperbolic trajectory (v > v_esc -> e > 1, T = inf)."""
        r_val = AU_METERS
        v_esc = math.sqrt(2.0 * self.mu_sun / r_val)
        v_hyper = v_esc * 1.25  # 25% over escape speed
        r = np.array([r_val, 0.0, 0.0])
        v = np.array([0.0, v_hyper, 0.0])

        elements = cartesian_to_keplerian(r, v, self.mu_sun)
        self.assertGreater(elements.eccentricity, 1.0)
        self.assertLess(elements.semi_major_axis, 0.0)
        self.assertEqual(elements.orbital_period, np.inf)

    def test_inclined_orbit(self):
        """45-degree inclined orbit properly resolves inclination."""
        r = np.array([AU_METERS, 0.0, 0.0])
        v_circ = math.sqrt(self.mu_sun / AU_METERS)
        # Velocity in Y-Z plane at 45 degrees
        v = np.array([0.0, v_circ * math.cos(math.pi / 4), v_circ * math.sin(math.pi / 4)])

        elements = cartesian_to_keplerian(r, v, self.mu_sun)
        self.assertAlmostEqual(elements.inclination, math.pi / 4, places=4)

    def test_numerical_guards(self):
        """Degenerate inputs must not cause division-by-zero crashes."""
        with self.assertRaises(ValueError):
            cartesian_to_keplerian(np.array([0.0, 0.0, 0.0]), np.array([100.0, 0.0, 0.0]), self.mu_sun)

        with self.assertRaises(ValueError):
            cartesian_to_keplerian(np.array([AU_METERS, 0.0, 0.0]), np.array([0.0, 100.0, 0.0]), -1.0)

        # Radial plunge trajectory (h = 0)
        r = np.array([AU_METERS, 0.0, 0.0])
        v = np.array([-1000.0, 0.0, 0.0])  # directly inward
        elements = cartesian_to_keplerian(r, v, self.mu_sun)
        self.assertEqual(elements.inclination, 0.0)


if __name__ == "__main__":
    unittest.main()
