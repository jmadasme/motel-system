#!/usr/bin/env bash
# Detiene el servidor central, sin importar cómo se haya arrancado.
cd "$(dirname "$0")"

if pgrep -f "python3 server/app.py" >/dev/null; then
  pkill -f "python3 server/app.py"
  sleep 1
  echo "[stop] servidor detenido"
else
  echo "[stop] el servidor no estaba corriendo"
fi
