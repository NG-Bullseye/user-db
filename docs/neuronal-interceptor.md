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

## Hotpath-Architektur (Policy-Cache; konsolidiert aus neural/CLAUDE.md, 2026-07-15)

Die Neural-Instanz ist **nicht** im Hotpath. Der Hotpath ist deterministisch: cortex `gateway.py::NeuralInterceptorLayer` (2s-Budget, fail-open) → `cortex:neural:hold:req` → `~/repos/watchdog/daemon/neural_hold.py` (systemd, ~3ms) → `cortex:neural:hold:reply`. Der Responder konsultiert vor seinem `default_pass` den **Policy-Cache**:

- Key: `cortex:neural:policy:<event>:<source>` (z.B. `cortex:neural:policy:SlotApplyEvent:SCHEDULER`)
- Value: JSON `{"verdict": "pass"|"modify"|"block", "reason": "…", "actions": […]}`
- **IMMER mit TTL schreiben** (`SET … EX <sekunden>`, Richtwert ≤ 3600) — Regeln verfallen, nichts gilt ewig
- Invalides JSON / invalider verdict / fehlender Key → Responder antwortet `pass` (fail-open)

Neural liest den req-Stream **read-only** (nie XDEL/XTRIM, nie den Cursor des Responders anfassen) über den `hold-req`-Monitor-Log (`~/.cache/neural/monitors/hold-req.log`) oder direkt via `docker exec cortex-redis redis-cli XREVRANGE cortex:neural:hold:req + - COUNT n`. Kontextquellen read-only: `summary`-Feld, `cortex:state.context_priming`, Cerebellum-Daten.

## Raumintensitäts-Daemon (Implementierung; konsolidiert aus neural/CLAUDE.md, 2026-07-15)

`daemon/room_intensity.py` im neural-Repo (systemd `neural-room-intensity.service`, Restart=always) bestimmt minütlich die **Raumintensität 0-100** aus der Raumszene (Musik+Volume, Beamer-Watt, PC-Watt, Zone; read-only aus `cortex:perception:head`) und meldet sie an die zentrale user-db (Glättung dort, s.o.). cortex spiegelt den geglätteten Wert als `sensor.user_db_room_intensity` in den Head zurück; der Watchdog wacht über die Frische (`user_state`-Block im Snapshot). Die Scoring-Verfeinerung (Szenen wie Kino: Bett+Beamer+PC-aus) gehört der Neural-Instanz — Szenen-Definition siehe oben (§ Scene recognition).

## Combining both axes

The interceptor additionally reads the current stress level
(`sensor_read("stress")`, produced by the watchdog agent). The freely
definable curve in `config.json` maps stress → target room intensity;
`state_get` returns `target` and `delta`. A positive delta means the room is
more intense than the user's stress level calls for — the hook for later
smart-home interactions.

## The weekly protocol (SOLL)

The interceptor executes a **weekly protocol**: a human-editable markdown file
in the data directory (`$USER_DB_DIR/wochen-protokoll.md`, outside this repo)
that describes 1:1 what the home is supposed to switch over the week (lights,
music, projector, motion scenes, per weekday and time) plus the target room
intensity per time window. The interceptor compares the live state against
this protocol — effective target = min(time baseline, curve(stress)) — and
raises an intervention request when reality diverges. Top-level behaviour
changes are made by editing the protocol text; the underlying automation
configs are then brought in line, never the other way around. A periodically
written observation log (the watchdog's tracking files) is the IST counterpart
for a future SOLL/IST weekly diff.
