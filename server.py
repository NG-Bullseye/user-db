#!/usr/bin/env python3
"""user-db MCP — central user profile + live virtual sensors (stress, room intensity).

Software only: all personal data lives outside the repo in USER_DB_DIR
(default ~/.config/user-db/). See README.md.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import core

mcp = FastMCP("user-db")


@mcp.tool()
def profile_get() -> dict:
    """Read the full user profile (name, speech_id, birthday, profession,
    expertise, durable traits, ...). Describes the user's durable state."""
    return core.get_profile()


@mcp.tool()
def profile_set(field: str, value: str) -> dict:
    """Set one profile field. `value` is parsed as JSON when possible
    (lists/numbers/null), otherwise stored as plain string. value="null"
    deletes the field. Returns the updated profile."""
    return core.set_profile_field(field, core.parse_value(value))


@mcp.tool()
def sensor_read(name: str = "stress") -> dict:
    """Read a virtual sensor (e.g. "stress", "room_intensity"): smoothed
    value, last raw observation, last update time."""
    return core.read_sensor(name)


@mcp.tool()
def sensor_report(name: str, value: float) -> dict:
    """Report a raw observation (0-100) for a virtual sensor. The stored
    value follows it smoothly (time-aware exponential smoothing; the
    tau_seconds reactiveness per sensor is set in config.json). Returns the
    new smoothed state. Use name="stress" for the user's stress level and
    name="room_intensity" for the room's current intensity."""
    return core.report_sensor(name, value)


@mcp.tool()
def state_get() -> dict:
    """Read the full live state: all virtual sensors plus the curve that
    combines both axes (target room intensity for the current stress level,
    and the delta between actual and target)."""
    return core.get_state()


if __name__ == "__main__":
    mcp.run()
