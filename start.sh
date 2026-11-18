#!/usr/bin/env bash
# Arranca el servidor central. Si no existe la base, la siembra con datos demo.
set -euo pipefail
cd "$(dirname "$0")"

if python3 -c 'import json,sys; sys.exit(0 if json.load(open("config.json"))["server"].get("https") else 1)'; then
  if [ ! -f server/certs/motel.pem ] || [ ! -f server/certs/motel.key ]; then
    echo "[start] HTTPS activo pero faltan los certificados: generandolos..."
    ./make_cert.sh
  else
    IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    if [ -n "$IP" ] && ! openssl x509 -in server/certs/motel.pem -noout -checkip "$IP" >/dev/null 2>&1; then
      echo "[start] AVISO: el certificado no cubre la IP actual ($IP)."
      echo "[start] Ejecuta ./make_cert.sh y reinicia para evitar errores de certificado."
    fi
  fi
fi

if [ ! -f data/motel.db ]; then
  echo "[start] base de datos no encontrada: sembrando demo..."
  python3 tools/seed_demo.py
fi

exec python3 server/app.py "$@"
