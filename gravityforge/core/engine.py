from __future__ import annotations

import dataclasses
from typing import List, Literal, Tuple
import numpy as np

# Physical constants (SI units: m, kg, s)
G_SI = 6.67430e-11  # m^3 kg^-1 s^-2
AU_METERS = 1.495978707e11
SOLAR_MASS_KG = 1.98847e30
DAY_SECONDS = 86400.0


@dataclasses.dataclass
class Body:
    name: str
    mass: float  # kg
    position: np.ndarray  # shape (3,) [m]
    velocity: np.ndarray  # shape (3,) [m/s]
    radius: float = 0.0  # m (visual/collision radius)
    color: str = "#FFFFFF"

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)
        self.velocity = np.asarray(self.velocity, dtype=np.float64)


def compute_accelerations(
    positions: np.ndarray, masses: np.ndarray, softening: float = 1e3, G: float = G_SI
) -> np.ndarray:
    """Vectorized pairwise gravitational acceleration.

    positions: shape (N, 3)
    masses: shape (N,)
    softening: gravitational softening length (meters) to avoid infinite divergence.
    returns: shape (N, 3) accelerations.
    """
    n = positions.shape[0]
    if n <= 1:
        return np.zeros_like(positions)

    # pairwise difference vectors: diff[i, j] = pos[j] - pos[i]
    diff = positions[np.newaxis, :, :] - positions[:, np.newaxis, :]  # (N, N, 3)

    # distance squared + softening
    dist_sq = np.sum(diff**2, axis=-1) + (softening**2)  # (N, N)
    dist = np.sqrt(dist_sq)  # (N, N)

    # zero out self-interaction
    np.fill_diagonal(dist_sq, np.inf)

    # a_i = sum_j (G * m_j * diff_ij / dist_ij^3)
    inv_dist_cube = 1.0 / (dist_sq * dist)
    np.fill_diagonal(inv_dist_cube, 0.0)

    # weights: G * m_j * inv_dist_cube[i, j]
    weights = G * masses[np.newaxis, :] * inv_dist_cube  # (N, N)

    # accelerations: sum along axis 1
    accelerations = np.einsum("ij,ijk->ik", weights, diff)
    return accelerations


def step_leapfrog(
    positions: np.ndarray,
    velocities: np.ndarray,
    masses: np.ndarray,
    dt: float,
    softening: float = 1e3,
    G: float = G_SI,
) -> Tuple[np.ndarray, np.ndarray]:
    """Symplectic Kick-Drift-Kick (Verlet/Leapfrog) integrator.

    Guarantees phase-space volume preservation and strict bounded energy drift.
    """
    # Half-step velocity kick
    acc_0 = compute_accelerations(positions, masses, softening=softening, G=G)
    v_half = velocities + 0.5 * dt * acc_0

    # Full-step position drift
    pos_new = positions + dt * v_half

    # Final half-step velocity kick
    acc_1 = compute_accelerations(pos_new, masses, softening=softening, G=G)
    vel_new = v_half + 0.5 * dt * acc_1

    return pos_new, vel_new


def step_rk4(
    positions: np.ndarray,
    velocities: np.ndarray,
    masses: np.ndarray,
    dt: float,
    softening: float = 1e3,
    G: float = G_SI,
) -> Tuple[np.ndarray, np.ndarray]:
    """Classic 4th-Order Runge-Kutta integrator.

    Provides high transient precision for close encounters and rapid gravitational slingshots.
    """
    # k1
    k1_v = velocities
    k1_a = compute_accelerations(positions, masses, softening=softening, G=G)

    # k2
    pos_k2 = positions + 0.5 * dt * k1_v
    vel_k2 = velocities + 0.5 * dt * k1_a
    k2_v = vel_k2
    k2_a = compute_accelerations(pos_k2, masses, softening=softening, G=G)

    # k3
    pos_k3 = positions + 0.5 * dt * k2_v
    vel_k3 = velocities + 0.5 * dt * k2_a
    k3_v = vel_k3
    k3_a = compute_accelerations(pos_k3, masses, softening=softening, G=G)

    # k4
    pos_k4 = positions + dt * k3_v
    vel_k4 = velocities + dt * k3_a
    k4_v = vel_k4
    k4_a = compute_accelerations(pos_k4, masses, softening=softening, G=G)

    pos_new = positions + (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v)
    vel_new = velocities + (dt / 6.0) * (k1_a + 2.0 * k2_a + 2.0 * k3_a + k4_a)
    return pos_new, vel_new


def compute_energy(
    positions: np.ndarray, masses: np.ndarray, velocities: np.ndarray, G: float = G_SI
) -> Tuple[float, float, float]:
    """Calculates Total Kinetic Energy, Gravitational Potential Energy, and Total Mechanical Energy."""
    v_sq = np.sum(velocities**2, axis=-1)
    e_kin = 0.5 * float(np.sum(masses * v_sq))

    n = positions.shape[0]
    e_pot = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            r = float(np.linalg.norm(positions[i] - positions[j]))
            if r > 0:
                e_pot -= (G * masses[i] * masses[j]) / r

    e_tot = e_kin + e_pot
    return e_kin, e_pot, e_tot


def compute_linear_momentum(masses: np.ndarray, velocities: np.ndarray) -> np.ndarray:
    """Calculates total linear momentum vector P = sum(m_i * v_i)."""
    return np.sum(masses[:, np.newaxis] * velocities, axis=0)


def compute_angular_momentum(
    positions: np.ndarray, masses: np.ndarray, velocities: np.ndarray
) -> np.ndarray:
    """Calculates total angular momentum vector L = sum(m_i * (r_i x v_i))."""
    r_cross_v = np.cross(positions, velocities)
    return np.sum(masses[:, np.newaxis] * r_cross_v, axis=0)


def compute_center_of_mass(positions: np.ndarray, masses: np.ndarray) -> np.ndarray:
    """Calculates center of mass position vector R_cm = sum(m_i * r_i) / sum(m_i)."""
    total_mass = float(np.sum(masses))
    if total_mass <= 0:
        return np.zeros(3, dtype=np.float64)
    return np.sum(masses[:, np.newaxis] * positions, axis=0) / total_mass


def compute_jacobi_constant(
    m1: float,
    m2: float,
    r1: np.ndarray,
    r2: np.ndarray,
    pos_test: np.ndarray,
    vel_test: np.ndarray,
    G: float = G_SI,
) -> float:
    """Computes Jacobi Constant C_J for a test particle in Circular Restricted 3-Body Problem (CR3BP).

    C_J = 2 * Omega(x, y) - v_rot^2
    """
    # Distance between primaries
    d = float(np.linalg.norm(r1 - r2))
    if d <= 0:
        return 0.0
    total_m = m1 + m2
    mean_motion = np.sqrt(G * total_m / (d**3))

    # Center of mass of primaries
    cm = (m1 * r1 + m2 * r2) / total_m

    # Relative coordinates to COM
    r_rel = pos_test - cm
    v_rel = vel_test

    # Rotating frame angular velocity vector along Z
    omega_vec = np.array([0.0, 0.0, mean_motion], dtype=np.float64)

    # Velocity in rotating frame: v_rot = v_inertial - (omega x r)
    v_rot = v_rel - np.cross(omega_vec, r_rel)
    v_rot_sq = float(np.sum(v_rot**2))

    # Potential terms
    d1 = float(np.linalg.norm(pos_test - r1))
    d2 = float(np.linalg.norm(pos_test - r2))
    u_grav = (G * m1 / d1) + (G * m2 / d2) if (d1 > 0 and d2 > 0) else 0.0
    u_centrif = 0.5 * (mean_motion**2) * (r_rel[0] ** 2 + r_rel[1] ** 2)

    c_j = 2.0 * (u_grav + u_centrif) - v_rot_sq
    return float(c_j)


class GravityEngine:
    """High-precision N-body simulation harness."""

    def __init__(
        self,
        bodies: List[Body],
        softening: float = 1e3,
        integrator: Literal["leapfrog", "rk4"] = "leapfrog",
        G: float = G_SI,
    ):
        self.bodies = bodies
        self.softening = softening
        self.integrator = integrator
        self.G = G
        self.time = 0.0

        self.names = [b.name for b in bodies]
        self.masses = np.array([b.mass for b in bodies], dtype=np.float64)
        self.positions = np.array([b.position for b in bodies], dtype=np.float64)
        self.velocities = np.array([b.velocity for b in bodies], dtype=np.float64)

        # Baseline conservation values
        self.initial_energy = self.current_energy()[2]
        self.initial_linear_momentum = self.current_linear_momentum()
        self.initial_angular_momentum = self.current_angular_momentum()

    def current_energy(self) -> Tuple[float, float, float]:
        return compute_energy(self.positions, self.masses, self.velocities, G=self.G)

    def current_linear_momentum(self) -> np.ndarray:
        return compute_linear_momentum(self.masses, self.velocities)

    def current_angular_momentum(self) -> np.ndarray:
        return compute_angular_momentum(self.positions, self.masses, self.velocities)

    def center_of_mass(self) -> np.ndarray:
        return compute_center_of_mass(self.positions, self.masses)

    def energy_relative_drift(self) -> float:
        """Returns |(E - E0) / E0| relative energy conservation error."""
        _, _, e_current = self.current_energy()
        if abs(self.initial_energy) < 1e-12:
            return 0.0
        return abs((e_current - self.initial_energy) / self.initial_energy)

    def momentum_relative_drift(self) -> Tuple[float, float]:
        """Returns relative drift for linear momentum and angular momentum."""
        p_curr = self.current_linear_momentum()
        p0_norm = float(np.linalg.norm(self.initial_linear_momentum))
        p_drift = (
            float(np.linalg.norm(p_curr - self.initial_linear_momentum)) / p0_norm
            if p0_norm > 1e-12
            else float(np.linalg.norm(p_curr))
        )

        l_curr = self.current_angular_momentum()
        l0_norm = float(np.linalg.norm(self.initial_angular_momentum))
        l_drift = (
            float(np.linalg.norm(l_curr - self.initial_angular_momentum)) / l0_norm
            if l0_norm > 1e-12
            else float(np.linalg.norm(l_curr))
        )
        return p_drift, l_drift

    def step(self, dt: float):
        """Advances simulation by dt seconds."""
        if self.integrator == "leapfrog":
            self.positions, self.velocities = step_leapfrog(
                self.positions, self.velocities, self.masses, dt, softening=self.softening, G=self.G
            )
        elif self.integrator == "rk4":
            self.positions, self.velocities = step_rk4(
                self.positions, self.velocities, self.masses, dt, softening=self.softening, G=self.G
            )
        else:
            raise ValueError(f"Unknown integrator: {self.integrator}")

        self.time += dt
        for i, b in enumerate(self.bodies):
            b.position = self.positions[i]
            b.velocity = self.velocities[i]
