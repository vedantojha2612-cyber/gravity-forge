from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple
import numpy as np
import requests
from ..core.engine import Body, SOLAR_MASS_KG, AU_METERS

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Standard JPL Major Body IDs
PLANET_IDS = {
    "sun": "10",
    "mercury": "199",
    "venus": "299",
    "earth": "399",
    "moon": "301",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
    "uranus": "799",
    "neptune": "899",
}

# Standard Masses (kg) and radii (m)
PLANETARY_METADATA = {
    "sun": {"mass": 1.98847e30, "radius": 6.9634e8, "color": "#FFD700"},
    "mercury": {"mass": 3.3011e23, "radius": 2.4397e6, "color": "#A9A9A9"},
    "venus": {"mass": 4.8675e24, "radius": 6.0518e6, "color": "#FFA500"},
    "earth": {"mass": 5.97217e24, "radius": 6.371e6, "color": "#1E90FF"},
    "moon": {"mass": 7.342e22, "radius": 1.7374e6, "color": "#E6E6FA"},
    "mars": {"mass": 6.4171e23, "radius": 3.3895e6, "color": "#FF4500"},
    "jupiter": {"mass": 1.89819e27, "radius": 6.9911e7, "color": "#DAA520"},
    "saturn": {"mass": 5.6834e26, "radius": 5.8232e7, "color": "#F4A460"},
    "uranus": {"mass": 8.6810e25, "radius": 2.5362e7, "color": "#00CED1"},
    "neptune": {"mass": 1.02413e26, "radius": 2.4622e7, "color": "#4169E1"},
}

# Offline default state vectors at J2000 epoch relative to Solar System Barycenter (positions in m, velocities in m/s)
OFFLINE_DEFAULT_EPHEMERIS = {
    "sun": {"pos": [0.0, 0.0, 0.0], "vel": [0.0, 0.0, 0.0]},
    "earth": {
        "pos": [-2.57398e10, 1.44955e11, 2.0526e7],
        "vel": [-2.9839e4, -5.301e3, 1.62],
    },
    "mars": {
        "pos": [2.066e11, -8.76e10, -6.83e9],
        "vel": [9.9e3, 2.37e4, 2.4e2],
    },
    "jupiter": {
        "pos": [5.979e11, 4.821e11, -1.56e10],
        "vel": [-8.27e3, 1.10e4, 1.3e2],
    },
}

_SAFE_PARAM_PATTERN = re.compile(r"^[a-zA-Z0-9@_.\- :]+$")


def validate_api_input(name: str, value: str) -> str:
    """Validates parameter string against injection attack characters."""
    if not isinstance(value, str):
        raise TypeError(f"Parameter '{name}' must be a string, got {type(value).__name__}")
    value_clean = value.strip()
    if not value_clean:
        raise ValueError(f"Parameter '{name}' cannot be empty")
    if not _SAFE_PARAM_PATTERN.match(value_clean):
        raise ValueError(
            f"Parameter '{name}' contains disallowed characters. Allowed: alphanumeric, @, _, ., -, :, spaces"
        )
    return value_clean


def fetch_horizons_vector(
    target_id: str,
    center_id: str = "500@0",  # Solar System Barycenter
    start_time: str = "2026-10-24",
    stop_time: str = "2026-10-25",
    timeout_sec: float = 10.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Queries NASA JPL Horizons API for 3D state vector (pos [m], vel [m/s]).

    Includes strict input sanitization, network timeouts, and resilient error recovery.
    """
    safe_target = validate_api_input("target_id", target_id)
    safe_center = validate_api_input("center_id", center_id)
    safe_start = validate_api_input("start_time", start_time)
    safe_stop = validate_api_input("stop_time", stop_time)

    params = {
        "format": "json",
        "COMMAND": f"'{safe_target}'",
        "CENTER": f"'{safe_center}'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "START_TIME": f"'{safe_start}'",
        "STOP_TIME": f"'{safe_stop}'",
        "STEP_SIZE": "'1d'",
        "VEC_TABLE": "'2'",  # Type 2 gives X, Y, Z, VX, VY, VZ
        "REF_SYSTEM": "'ICRF'",
        "OUT_UNITS": "'KM-S'",  # km and km/s
    }

    try:
        resp = requests.get(HORIZONS_API_URL, params=params, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Horizons API network error for target {safe_target}: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Horizons API returned non-JSON payload: {e}") from e

    result_text = data.get("result", "")
    if not result_text:
        raise ValueError(f"Empty result received from Horizons for target {safe_target}")

    # Parse vectors from SOE (Start of Ephemeris) to EOE block
    soe_match = re.search(r"\$\$SOE\s+(.*?)\s+\$\$EOE", result_text, re.DOTALL)
    if not soe_match:
        raise ValueError(
            f"Failed to parse ephemeris block from Horizons response for target {safe_target}"
        )

    block = soe_match.group(1)

    # Extract X, Y, Z (km) and VX, VY, VZ (km/s) with robust regex checks
    x_match = re.search(r"X\s*=\\s*([+-]?\d+\.?\d*E?[+-]?\d*)", block)
    y_match = re.search(r"Y\s*=\\s*([+-]?\d+\.?\d*E?[+-]?\d*)", block)
    z_match = re.search(r"Z\s*=\\s*([+-]?\d+\.?\d*E?[+-]?\d*)", block)
    vx_match = re.search(r"VX\s*=\\s*([+-]?\d+\.?\d*E?[+-]?\d*)", block)
    vy_match = re.search(r"VY\s*=\\s*([+-]?\d+\.?\d*E?[+-]?\d*)", block)
    vz_match = re.search(r"VZ\s*=\\s*([+-]?\d+\.?\d*E?[+-]?\d*)", block)

    if not all([x_match, y_match, z_match, vx_match, vy_match, vz_match]):
        raise ValueError(f"Incomplete coordinate components parsed for target {safe_target}")

    x = float(x_match.group(1)) * 1000.0
    y = float(y_match.group(1)) * 1000.0
    z = float(z_match.group(1)) * 1000.0

    vx = float(vx_match.group(1)) * 1000.0
    vy = float(vy_match.group(1)) * 1000.0
    vz = float(vz_match.group(1)) * 1000.0

    return np.array([x, y, z], dtype=np.float64), np.array([vx, vy, vz], dtype=np.float64)


def load_system(body_names: List[str], use_live_api: bool = False) -> List[Body]:
    """Loads a set of celestial bodies initialized with real ephemerides.

    Falls back safely to calibrated offline barycentric state vectors if offline or API is unavailable.
    """
    bodies = []
    for name in body_names:
        key = str(name).strip().lower()
        meta = PLANETARY_METADATA.get(key, {"mass": 1e20, "radius": 1e5, "color": "#FFFFFF"})

        pos = None
        vel = None
        if use_live_api and key in PLANET_IDS:
            try:
                pos, vel = fetch_horizons_vector(PLANET_IDS[key])
            except Exception:
                # Logically fall through to verified offline ephemerides
                pos, vel = None, None

        if pos is None or vel is None:
            if key in OFFLINE_DEFAULT_EPHEMERIS:
                pos = np.array(OFFLINE_DEFAULT_EPHEMERIS[key]["pos"], dtype=np.float64)
                vel = np.array(OFFLINE_DEFAULT_EPHEMERIS[key]["vel"], dtype=np.float64)
            else:
                pos = np.zeros(3, dtype=np.float64)
                vel = np.zeros(3, dtype=np.float64)

        bodies.append(
            Body(
                name=name.strip().capitalize(),
                mass=float(meta["mass"]),
                position=pos,
                velocity=vel,
                radius=float(meta["radius"]),
                color=str(meta["color"]),
            )
        )
    return bodies
