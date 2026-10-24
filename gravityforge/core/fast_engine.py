from __future__ import annotations

from typing import List, Literal, Tuple
import numpy as np

from gravityforge.core.engine import Body, GravityEngine, G_SI, AU_METERS, compute_energy


class FastGravityEngine(GravityEngine):
    """Zero-allocation high-throughput N-body simulation engine.

    Preallocates all internal matrices (pairwise vectors, squared distances,
    inverse cube distance weights, and intermediate velocity/acceleration stages).
    Eliminates GC churn and memory fragmentation in high-frequency calculation loops.
    """

    def __init__(
        self,
        bodies: List[Body],
        softening: float = 1e3,
        integrator: Literal["leapfrog", "rk4"] = "leapfrog",
        G: float = G_SI,
    ):
        super().__init__(bodies, softening=softening, integrator=integrator, G=G)
        self.n = len(bodies)
        self.softening_sq = float(softening**2)

        # Preallocated buffers for O(N^2) pairwise force interactions
        self._diff = np.empty((self.n, self.n, 3), dtype=np.float64)
        self._dist_sq = np.empty((self.n, self.n), dtype=np.float64)
        self._dist = np.empty((self.n, self.n), dtype=np.float64)
        self._inv_dist_cube = np.empty((self.n, self.n), dtype=np.float64)
        self._weights = np.empty((self.n, self.n), dtype=np.float64)

        # Preallocated acceleration and stage buffers
        self._acc0 = np.empty((self.n, 3), dtype=np.float64)
        self._acc1 = np.empty((self.n, 3), dtype=np.float64)
        self._v_half = np.empty((self.n, 3), dtype=np.float64)

        # RK4 intermediate stage buffers
        self._k1_v = np.empty((self.n, 3), dtype=np.float64)
        self._k1_a = np.empty((self.n, 3), dtype=np.float64)
        self._k2_v = np.empty((self.n, 3), dtype=np.float64)
        self._k2_a = np.empty((self.n, 3), dtype=np.float64)
        self._k3_v = np.empty((self.n, 3), dtype=np.float64)
        self._k3_a = np.empty((self.n, 3), dtype=np.float64)
        self._k4_v = np.empty((self.n, 3), dtype=np.float64)
        self._k4_a = np.empty((self.n, 3), dtype=np.float64)
        self._pos_tmp = np.empty((self.n, 3), dtype=np.float64)

    def _compute_accelerations_inplace(self, pos: np.ndarray, out_acc: np.ndarray) -> None:
        """In-place pairwise gravitational acceleration calculation."""
        # Pairwise differences: diff[i, j] = pos[j] - pos[i]
        np.subtract(pos[np.newaxis, :, :], pos[:, np.newaxis, :], out=self._diff)

        # Distance squared + softening
        np.sum(self._diff**2, axis=-1, out=self._dist_sq)
        self._dist_sq += self.softening_sq

        # Euclidean distances
        np.sqrt(self._dist_sq, out=self._dist)

        # Avoid zero division on diagonal
        np.fill_diagonal(self._dist_sq, np.inf)

        # inv_dist_cube = 1.0 / (dist_sq * dist)
        np.multiply(self._dist_sq, self._dist, out=self._inv_dist_cube)
        np.divide(1.0, self._inv_dist_cube, out=self._inv_dist_cube)
        np.fill_diagonal(self._inv_dist_cube, 0.0)

        # weights = G * masses[j] * inv_dist_cube[i, j]
        np.multiply(self.G * self.masses[np.newaxis, :], self._inv_dist_cube, out=self._weights)

        # Contraction: sum_j weights[i, j] * diff[i, j, k]
        np.einsum("ij,ijk->ik", self._weights, self._diff, out=out_acc)

    def step(self, dt: float) -> None:
        """Advances simulation by dt seconds with zero heap reallocations."""
        if self.integrator == "leapfrog":
            self._step_leapfrog_inplace(dt)
        elif self.integrator == "rk4":
            self._step_rk4_inplace(dt)
        else:
            raise ValueError(f"Unknown integrator: {self.integrator}")

        self.time += dt

    def _step_leapfrog_inplace(self, dt: float) -> None:
        # 1. acc_0 = a(pos)
        self._compute_accelerations_inplace(self.positions, self._acc0)

        # 2. v_half = vel + 0.5 * dt * acc_0
        np.multiply(self._acc0, 0.5 * dt, out=self._v_half)
        self._v_half += self.velocities

        # 3. pos_new = pos + dt * v_half
        self.positions += dt * self._v_half

        # 4. acc_1 = a(pos_new)
        self._compute_accelerations_inplace(self.positions, self._acc1)

        # 5. vel_new = v_half + 0.5 * dt * acc_1
        np.multiply(self._acc1, 0.5 * dt, out=self.velocities)
        self.velocities += self._v_half

    def _step_rk4_inplace(self, dt: float) -> None:
        # k1
        np.copyto(self._k1_v, self.velocities)
        self._compute_accelerations_inplace(self.positions, self._k1_a)

        # k2
        np.multiply(self._k1_v, 0.5 * dt, out=self._pos_tmp)
        self._pos_tmp += self.positions
        np.multiply(self._k1_a, 0.5 * dt, out=self._k2_v)
        self._k2_v += self.velocities
        self._compute_accelerations_inplace(self._pos_tmp, self._k2_a)

        # k3
        np.multiply(self._k2_v, 0.5 * dt, out=self._pos_tmp)
        self._pos_tmp += self.positions
        np.multiply(self._k2_a, 0.5 * dt, out=self._k3_v)
        self._k3_v += self.velocities
        self._compute_accelerations_inplace(self._pos_tmp, self._k3_a)

        # k4
        np.multiply(self._k3_v, dt, out=self._pos_tmp)
        self._pos_tmp += self.positions
        np.multiply(self._k3_a, dt, out=self._k4_v)
        self._k4_v += self.velocities
        self._compute_accelerations_inplace(self._pos_tmp, self._k4_a)

        # Final state update: pos += dt/6 * (k1_v + 2*k2_v + 2*k3_v + k4_v)
        dt_6 = dt / 6.0
        self.positions += dt_6 * (self._k1_v + 2.0 * self._k2_v + 2.0 * self._k3_v + self._k4_v)
        self.velocities += dt_6 * (self._k1_a + 2.0 * self._k2_a + 2.0 * self._k3_a + self._k4_a)

    def sync_bodies(self) -> None:
        """Syncs position/velocity arrays back to Body objects when requested."""
        for i, b in enumerate(self.bodies):
            b.position = self.positions[i].copy()
            b.velocity = self.velocities[i].copy()
