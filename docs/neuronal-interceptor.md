# Neuronal Interceptor — the room-intensity agent

The second axis of the system is produced by a **scene-analysis agent** ("neuronal
interceptor"): an LLM agent that reads its configuration through the neuronal
interceptor layer, analyses the current room situation, and reports the
**room intensity** — a value between 0 and 100 — via `sensor_report("room_intensity", x)`.

## Inputs (signals it may combine)

- current music and genre
- playback volume
- projector (beamer) active
- currently playing media
- PC state (on / mostly off)
- user presence in bed
- any further hints about the current scene

## Scene recognition

The agent recognises scenes from signal combinations. Example — *cinema*:

- user is lying in bed
- projector is active
- PC is mostly off

→ high media focus, moderate intensity; the agent describes the room's current
state as one number plus (optionally) a scene label in its own log.

The exact scoring definition is intentionally open and will be refined later;
the contract is only: **0 = silent/idle room, 100 = maximum intensity**, report
raw observations and let user-db's smoothing produce the stable sensor.

## Combining both axes

The interceptor additionally reads the current stress level
(`sensor_read("stress")`, produced by the watchdog agent). The freely
definable curve in `config.json` maps stress → target room intensity;
`state_get` returns `target` and `delta`. A positive delta means the room is
more intense than the user's stress level calls for — the hook for later
smart-home interactions.
