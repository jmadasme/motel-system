#!/usr/bin/env bash
# ¿Está corriendo el servidor? Muestra estado y URLs de acceso.
cd "$(dirname "$0")"

PID=$(pgrep -f "python3 server/app.py" | head -1 || true)
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
IP="${IP:-127.0.0.1}"
SCHEME=$(python3 -c 'import json; print("https" if json.load(open("config.json"))["server"].get("https") else "http")' 2>/dev/null || echo http)

if [ -n "$PID" ]; then
  echo "[status] SERVIDOR CORRIENDO (pid $PID)"
  echo "  Recepcion : $SCHEME://$IP:8080/recepcion"
  echo "  Escaner   : $SCHEME://$IP:8080/scan?cab=1"
  echo "  Catalogo  : $SCHEME://$IP:8080/cabana?cab=1"
  echo "  Cocina    : $SCHEME://$IP:8080/kitchen"
  echo "  Panel     : $SCHEME://$IP:8080/dashboard"
  echo "  Ingresos  : $SCHEME://$IP:8080/ingresos"
  echo "  Maquetas  : $SCHEME://$IP:8080/maquetas/index.html"
else
  echo "[status] el servidor NO esta corriendo. Arrancar con: ./start.sh"
fi
