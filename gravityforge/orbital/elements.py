from __future__ import annotations

import dataclasses
import numpy as np
from typing import Tuple


@dataclasses.dataclass
class KeplerianElements:
    semi_major_axis: float  # a [m]
    eccentricity: float  # e (dimensionless)
    inclination: float  # i [radians]
    longitude_ascending_node: float  # Omega [radians]
    argument_of_periapsis: float  # omega [radians]
    true_anomaly: float  # nu [radians]
    orbital_period: float  # T [seconds] (for elliptic orbits)


def cartesian_to_keplerian(
    r_vec: np.ndarray, v_vec: np.ndarray, mu: float
) -> KeplerianElements:
    """Converts 3D Cartesian position and velocity vectors to Keplerian orbital elements.

    r_vec: position vector [x, y, z] in meters relative to central body
    v_vec: velocity vector [vx, vy, vz] in m/s relative to central body
    mu: standard gravitational parameter G * (M + m) [m^3/s^2]
    """
    r_vec = np.asarray(r_vec, dtype=np.float64)
    v_vec = np.asarray(v_vec, dtype=np.float64)

    r = float(np.linalg.norm(r_vec))
    v = float(np.linalg.norm(v_vec))

    if r < 1e-9:
        raise ValueError("Position vector magnitude must be strictly non-zero.")
    if mu <= 0:
        raise ValueError("Standard gravitational parameter mu must be strictly positive.")

    # Specific angular momentum vector h = r x v
    h_vec = np.cross(r_vec, v_vec)
    h = float(np.linalg.norm(h_vec))

    # Node vector n = k x h = [-h_y, h_x, 0]
    n_vec = np.array([-h_vec[1], h_vec[0], 0.0], dtype=np.float64)
    n = float(np.linalg.norm(n_vec))

    # Eccentricity vector e_vec
    e_vec = (1.0 / mu) * ((v**2 - mu / r) * r_vec - np.dot(r_vec, v_vec) * v_vec)
    e = float(np.linalg.norm(e_vec))

    # Specific orbital energy
    energy = 0.5 * (v**2) - (mu / r)

    # Semi-major axis
    if abs(e - 1.0) > 1e-7 and abs(energy) > 1e-14:
        a = -mu / (2.0 * energy)
    else:
        a = np.inf  # Parabolic

    # Inclination (guarded against h == 0 for rectilinear trajectories)
    if h > 1e-12:
        inc = float(np.arccos(np.clip(h_vec[2] / h, -1.0, 1.0)))
    else:
        inc = 0.0

    # Longitude of ascending node (Omega)
    if n > 1e-9:
        omega_node = float(np.arccos(np.clip(n_vec[0] / n, -1.0, 1.0)))
        if n_vec[1] < 0:
            omega_node = 2.0 * np.pi - omega_node
    else:
        omega_node = 0.0

    # Argument of periapsis (omega)
    if n > 1e-9 and e > 1e-7:
        arg_peri = float(np.arccos(np.clip(np.dot(n_vec, e_vec) / (n * e), -1.0, 1.0)))
        if e_vec[2] < 0:
            arg_peri = 2.0 * np.pi - arg_peri
    else:
        arg_peri = 0.0

    # True anomaly (nu)
    if e > 1e-7:
        true_anom = float(np.arccos(np.clip(np.dot(e_vec, r_vec) / (e * r), -1.0, 1.0)))
        if np.dot(r_vec, v_vec) < 0:
            true_anom = 2.0 * np.pi - true_anom
    else:
        true_anom = 0.0

    # Orbital period (for bound elliptic orbits)
    period = float(2.0 * np.pi * np.sqrt((a**3) / mu)) if (a > 0 and np.isfinite(a)) else np.inf

    return KeplerianElements(
        semi_major_axis=float(a),
        eccentricity=float(e),
        inclination=float(inc),
        longitude_ascending_node=float(omega_node),
        argument_of_periapsis=float(arg_peri),
        true_anomaly=float(true_anom),
        orbital_period=float(period),
    )
