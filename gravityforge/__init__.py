"""GravityForge: High-Performance Symplectic N-Body and Relativistic Slingshot Trajectory Engine."""

__version__ = "1.0.0"

from .core.engine import (
    Body,
    GravityEngine,
    compute_accelerations,
    step_leapfrog,
    step_rk4,
    compute_energy,
)
from .core.fast_engine import FastGravityEngine
from .orbital.elements import KeplerianElements, cartesian_to_keplerian
from .ephemeris.jpl import load_system, fetch_horizons_vector
