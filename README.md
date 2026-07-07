# user-db

Central user-state database as an MCP server: durable profile facts plus
**live virtual sensors** (user stress level, room intensity) with configurable
smoothing — readable in real time by any agent or smart-home service.

## Data separation (important)

This repository contains **software only**. All personal data lives outside
the repo, in the directory given by `USER_DB_DIR` (default `~/.config/user-db/`):

| File | Content | Written by |
|---|---|---|
| `profile.json` | durable user facts (name, speech id, birthday, profession, expertise, traits, ...) | you / agents via `profile_set` |
| `config.json` | sensor + curve configuration (reactiveness tuning) | you |
| `state.json` | live sensor state | this software |

Nothing in this repo ever contains user data; `examples/` holds neutral
templates. Copy them to `USER_DB_DIR` to get started:

```bash
mkdir -p ~/.config/user-db
cp examples/*.json ~/.config/user-db/
```

## Install & run

```bash
python3 -m venv .venv && .venv/bin/pip install mcp
claude mcp add --scope user user-db -- $PWD/.venv/bin/python $PWD/server.py
```

CLI (same core, for shell loops and Home Assistant `command_line` sensors):

```bash
bin/userdb profile
bin/userdb sensor report stress 70
bin/userdb sensor read stress
bin/userdb state
```

## MCP tools

- `profile_get` / `profile_set(field, value)` — the user's durable state.
- `sensor_read(name)` / `sensor_report(name, value)` — virtual sensors.
- `state_get` — all sensors + the curve combining both axes.

## Virtual sensors & reactiveness

A sensor value is not a plain variable. Producers report **raw observations**
(0–100); the stored value follows them via time-aware exponential smoothing:

```
alpha = 1 - exp(-dt / tau_seconds)
value += alpha * (raw - value)
```

`tau_seconds` per sensor in `config.json` is the **reactiveness**: small tau =
reactive, large tau = inert. This keeps the sensor from jumping and lets you
fine-tune it for smart-home automations. The first report initialises the
value directly.

Default sensors: `stress` (the user's stress level, reported by a
watchdog/perception agent) and `room_intensity` (the room's current scene
intensity, reported by a scene-analysis agent — see
[docs/neuronal-interceptor.md](docs/neuronal-interceptor.md)).

## The two axes & the curve

The system has two orthogonal axes: **user stress** and **room intensity**.
A freely definable piecewise-linear curve in `config.json` maps stress to a
*target* room intensity:

```json
"curve": {"x": "stress", "y": "room_intensity",
          "points": [[0, 85], [40, 60], [70, 35], [100, 15]]}
```

`state_get` evaluates it and returns `target` and `delta` (actual − target) —
the basis for smart-home decisions ("the user is stressed but the room is
loud → calm it down").

## Home Assistant

Expose the smoothed value as a `command_line` sensor, or bridge it through an
existing MCP that already abstracts Home Assistant:

```yaml
sensor:
  - platform: command_line
    name: user_stress
    command: "/path/to/user-db/bin/userdb sensor read stress | jq .value"
    scan_interval: 60
```

## License

MIT
