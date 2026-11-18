#!/usr/bin/env bash
# Genera un certificado autofirmado para servir por HTTPS.
# Necesario para que los telefonos puedan abrir la CAMARA con Chrome
# (getUserMedia solo funciona en https:// o localhost).
set -euo pipefail
cd "$(dirname "$0")"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
IP="${IP:-127.0.0.1}"

mkdir -p server/certs
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout server/certs/motel.key \
  -out server/certs/motel.pem \
  -subj "/CN=motel.local" \
  -addext "subjectAltName=DNS:motel.local,DNS:localhost,IP:${IP},IP:127.0.0.1"

# Copia publica para instalar como CA en los telefonos (via HTTP).
cp server/certs/motel.pem server/web/motel.crt

# Deja HTTPS activado: sin esto el servidor sigue en HTTP y la camara no funciona.
python3 - <<'PY'
import json
with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)
cfg.setdefault("server", {})["https"] = True
with open("config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY

echo
echo "Certificado generado para la IP ${IP} y HTTPS activado en config.json."
echo "1) Reinicia el servidor:  ./restart.sh"
echo "2) En cada equipo abre:  https://${IP}:8080  y acepta el aviso de seguridad."
