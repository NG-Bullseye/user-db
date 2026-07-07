"""user-db core — user profile storage + virtual sensors with smoothing.

All user data lives OUTSIDE the repository, in the directory given by the
environment variable USER_DB_DIR (default: ~/.config/user-db/):

    profile.json   durable user facts (name, speech_id, birthday, traits, ...)
    config.json    sensor + curve configuration (reactiveness tuning)
    state.json     live sensor state, written by this module

Sensors are "virtual sensors": a raw value is reported by a producer
(e.g. the watchdog agent reporting stress), and a time-aware exponential
smoothing algorithm turns it into a stable, non-jumpy sensor reading.
The smoothing constant tau_seconds is the configurable *reactiveness*:
small tau = reactive, large tau = inert.
"""
from __future__ import annotations

import fcntl
import json
import math
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.environ.get("USER_DB_DIR", "~/.config/user-db")).expanduser()
PROFILE_FILE = DATA_DIR / "profile.json"
CONFIG_FILE = DATA_DIR / "config.json"
STATE_FILE = DATA_DIR / "state.json"
LOCK_FILE = DATA_DIR / ".lock"

DEFAULT_CONFIG = {
    "sensors": {
        # tau_seconds = reactiveness: time constant of the exponential
        # smoothing. Small = reactive, large = inert.
        "stress": {"min": 0, "max": 100, "tau_seconds": 600},
        "room_intensity": {"min": 0, "max": 100, "tau_seconds": 120},
    },
    # Piecewise-linear curve mapping the x-sensor to a *target* value for
    # the y-sensor. Default: the more stressed the user, the calmer the
    # room should be.
    "curve": {
        "x": "stress",
        "y": "room_intensity",
        "points": [[0, 85], [40, 60], [70, 35], [100, 15]],
    },
}


# ---- Storage ----------------------------------------------------------------
def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


@contextmanager
def _locked():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_config() -> dict:
    return _deep_merge(DEFAULT_CONFIG, _read_json(CONFIG_FILE, {}))


# ---- Profile ----------------------------------------------------------------
def get_profile() -> dict:
    return _read_json(PROFILE_FILE, {})


def set_profile_field(field: str, value):
    """Set (or delete, with value=None) one profile field. Returns the profile."""
    with _locked():
        profile = _read_json(PROFILE_FILE, {})
        if value is None:
            profile.pop(field, None)
        else:
            profile[field] = value
        _write_json(PROFILE_FILE, profile)
    return profile


# ---- Virtual sensors --------------------------------------------------------
def _sensor_config(name: str) -> dict:
    sensors = get_config()["sensors"]
    if name not in sensors:
        raise KeyError(f"unknown sensor {name!r} — configured: {sorted(sensors)}")
    return sensors[name]


def read_sensor(name: str) -> dict:
    _sensor_config(name)
    return _read_json(STATE_FILE, {}).get(name, {"value": None, "raw": None, "updated_at": None})


def report_sensor(name: str, raw: float, now: float | None = None) -> dict:
    """Report a raw observation; the stored value follows it smoothly.

    Time-aware exponential smoothing: alpha = 1 - exp(-dt / tau), so the
    stored value converges toward the raw input with time constant tau
    regardless of how irregularly observations arrive. The first report
    initialises the value directly.
    """
    cfg = _sensor_config(name)
    now = time.time() if now is None else now
    raw = max(cfg["min"], min(cfg["max"], float(raw)))
    with _locked():
        state = _read_json(STATE_FILE, {})
        prev = state.get(name)
        if not prev or prev.get("value") is None:
            value = raw
        else:
            dt = max(0.0, now - (prev.get("updated_at") or now))
            alpha = 1.0 - math.exp(-dt / max(1e-6, cfg["tau_seconds"]))
            value = prev["value"] + alpha * (raw - prev["value"])
        state[name] = {
            "value": round(value, 2),
            "raw": raw,
            "updated_at": now,
            "updated_iso": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds"),
        }
        _write_json(STATE_FILE, state)
    return state[name]


# ---- Curve ------------------------------------------------------------------
def eval_curve(x: float, points: list) -> float:
    """Piecewise-linear interpolation over sorted [x, y] control points."""
    pts = sorted((float(a), float(b)) for a, b in points)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def get_state() -> dict:
    """All sensors plus the curve evaluation combining both axes."""
    cfg = get_config()
    sensors = {name: read_sensor(name) for name in cfg["sensors"]}
    curve = cfg["curve"]
    x_val = sensors.get(curve["x"], {}).get("value")
    y_val = sensors.get(curve["y"], {}).get("value")
    out = {"sensors": sensors, "curve": None}
    if x_val is not None:
        target = round(eval_curve(x_val, curve["points"]), 2)
        out["curve"] = {
            "x": curve["x"],
            "y": curve["y"],
            "target": target,
            "delta": None if y_val is None else round(y_val - target, 2),
        }
    return out
