# ARCHITECTURE — user-db

## Deep Modules — Rohbeobachtung → geglätteter Sensor → Kurve

Der Hauptflow nimmt Rohwerte (0–100) virtueller Sensoren entgegen, glättet sie zeitabhängig exponentiell und bewertet eine Kurve Stress → Soll-Raumintensität. Kern `core.py`, zwei Fassaden: `server.py` (MCP) und `bin/userdb` (CLI). Nutzdaten nur in `USER_DB_DIR`, nie im Repo. Jede Innenleben-Zelle ist datei:zeile und muss per grep -n treffen.

## Flow

**Sequenz** (`core.py:133 def report_sensor`)

| # | Modul | Eingang | Ausgang | Bedingung | Stellschraube | Innenleben |
|---|---|---|---|---|---|---|
| 1 | Sensor-Konfiguration | Sensorname | min/max/tau | — | `tau_seconds` in `config.json` | `core.py:121 def _sensor_config` |
| 2 | Glättung | Rohwert, Zeit | neuer Wert in `state.json` | erster Report setzt direkt | `tau_seconds` | `core.py:133 def report_sensor` |
| 3 | Kurve | Stress | Soll-Intensität | stückweise linear | `curve.points` | `core.py:167 def eval_curve` |
| 4 | Zustand | alle Sensoren | `target`, `delta` | — | — | `core.py:179 def get_state` |

**Parallel**

| Modul | Eingang | Ausgang | Bedingung | Stellschraube | Innenleben |
|---|---|---|---|---|---|
| Profil | Feld, Wert | `profile.json` | Dateisperre | — | `core.py:108 def set_profile_field` |
| MCP-Tools | `profile_*`, `sensor_*`, `state_get` | JSON | stdio | — | `server.py:39 def sensor_report` |
| CLI | `userdb …` | JSON auf stdout | — | — | `bin/userdb:22 def main` |
| Kalibrier-CLI | `kalib intensity|log` | `soll-intensity.json`, Wochen-Protokoll | — | — | `bin/kalib:94 def main` |

## Schnittstellen

- Datenverzeichnis `USER_DB_DIR` (Default `~/.config/user-db`, `core.py:27 DATA_DIR`), Vorlagen in `examples/`.
- Interceptor-Konzept: `docs/neuronal-interceptor.md`.

## Standard: Deep Modules + Flow

Kanon: `~/repos/speech-engine/ARCHITECTURE.md` § Standard (R1–R5).
