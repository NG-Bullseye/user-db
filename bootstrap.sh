#!/usr/bin/env bash
# bootstrap.sh — Setup-Einstieg fuer user-db (Leo 2026-09-29: "Bootstrailer fuer alle repos").
# Idempotent: legt nur fehlendes an, kann beliebig oft laufen.
# Startet keinen Dienst, schreibt nichts nach ~/.claude oder systemd.
set -euo pipefail
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
[ -x .venv/bin/python ] || "${PYTHON:-python3}" -m venv .venv
# Kein pip install -e . (flat layout ohne Paket) — Abhaengigkeiten direkt aus pyproject.toml, eine Quelle.
.venv/bin/python -c 'import tomllib; print("\n".join(tomllib.load(open("pyproject.toml","rb"))["project"]["dependencies"]))' \
  | xargs -r .venv/bin/pip install -q
# Datenverzeichnis ausserhalb des Repos (README § Data separation); Vorlagen nur, wo noch keine Datei liegt.
DATA_DIR="${USER_DB_DIR:-$HOME/.config/user-db}"
mkdir -p "$DATA_DIR"
for f in examples/*.json; do [ -e "$DATA_DIR/${f##*/}" ] || cp "$f" "$DATA_DIR/"; done
echo "bootstrap ok: $(pwd)"
