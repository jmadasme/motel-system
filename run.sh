#!/usr/bin/env bash
# Prepara la demo publica del motel:
#   - inicia el servidor local (HTTPS 8080 + HTTP 8081)
#   - abre un tunel temporal de Cloudflare con HTTPS valido
#   - genera los enlaces para enviar por WhatsApp
#
# Uso:
#   ./run.sh          inicia todo y muestra los enlaces
#   ./run.sh stop     cierra solo el tunel publico
set -euo pipefail
cd "$(dirname "$0")"

DATA="data"
PIDFILE="$DATA/cloudflared.pid"
TUNLOG="$DATA/tunnel.log"
LINKS="$DATA/demo_links.txt"
WA="$DATA/demo_whatsapp.txt"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/motel-demo"
CF="$CACHE/cloudflared"

stop_tunnel() {
  if [ -f "$PIDFILE" ]; then
    local pid
    pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$PIDFILE"
  fi
  # Cierra cualquier tunel anterior de este proyecto.
  local pid
  for pid in $(pgrep -f "[c]loudflared tunnel --url http://localhost:8081" || true); do
    kill "$pid" 2>/dev/null || true
  done
}

if [ "${1:-start}" = "stop" ]; then
  stop_tunnel
  echo "[demo] tunel publico cerrado. El servidor local sigue disponible."
  exit 0
fi

mkdir -p "$DATA" "$CACHE"

# 1. Servidor local ---------------------------------------------------------
if pgrep -f "python3 server/app.py" >/dev/null 2>&1; then
  echo "[demo] servidor local ya esta corriendo"
else
  echo "[demo] iniciando servidor local..."
  nohup ./start.sh > "$DATA/server.out" 2>&1 &
  sleep 2
fi

ok=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 http://127.0.0.1:8081/api/config >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 1
done
if [ "$ok" != "1" ]; then
  echo "[demo] ERROR: el servidor no responde en el puerto 8081."
  tail -n 30 "$DATA/server.out" 2>/dev/null || true
  exit 1
fi

# 2. Binario de Cloudflare --------------------------------------------------
if [ ! -x "$CF" ]; then
  if command -v cloudflared >/dev/null 2>&1; then
    CF=$(command -v cloudflared)
  else
    echo "[demo] descargando cloudflared (solo la primera vez)..."
    curl -fL --retry 3 --max-time 300 -o "$CF.part" \
      https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    chmod +x "$CF.part"
    mv "$CF.part" "$CF"
  fi
fi

# 3. Tunel publico ----------------------------------------------------------
stop_tunnel
: > "$TUNLOG"
echo "[demo] abriendo tunel publico..."
nohup "$CF" tunnel --url http://localhost:8081 --no-autoupdate --protocol http2 --edge-ip-version 4 > "$TUNLOG" 2>&1 &
echo $! > "$PIDFILE"

URL=""
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNLOG" 2>/dev/null | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done

if [ -z "$URL" ]; then
  echo "[demo] ERROR: no se pudo crear el tunel."
  tail -n 30 "$TUNLOG" 2>/dev/null || true
  stop_tunnel
  exit 1
fi

ok=0
for _ in $(seq 1 10); do
  if curl -fsS --max-time 5 "$URL/api/config" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [ "$ok" != "1" ]; then
  echo "[demo] AVISO: el tunel aun no responde; espera unos segundos."
fi

# 4. Enlaces ---------------------------------------------------------------
LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
LOCAL_IP="${LOCAL_IP:-127.0.0.1}"
python3 - "$URL" "$LINKS" "$WA" "x.txt" "$LOCAL_IP" <<'PY'
import json
import sys
import urllib.request

base, links_path, wa_path, x_path, local_ip = sys.argv[1:6]
with urllib.request.urlopen("http://127.0.0.1:8081/api/state", timeout=10) as r:
    state = json.load(r)
cabins = state.get("cabins", [])

lines = []
lines.append("=" * 66)
lines.append(" DEMO MOTEL - ENLACES PUBLICOS")
lines.append(" HTTPS valido, sin certificado. Sirven desde cualquier red.")
lines.append("=" * 66)
lines.append("")
lines.append("MENU / TODAS LAS PAGINAS")
lines.append(f"  {base}/")
lines.append("")
for name, path in (("RECEPCION", "/recepcion"),
                   ("COCINA", "/kitchen"),
                   ("PANEL", "/dashboard"),
                   ("INGRESOS", "/ingresos"),
                   ("MAQUETAS", "/maquetas/index.html")):
    lines.append(name)
    lines.append(f"  {base}{path}")
    lines.append("")
lines.append("CABANAS - ESCANER DE PUERTA Y PEDIDOS")
for c in cabins:
    cid = c.get("id")
    key = c.get("scanner_key", "")
    lines.append(f"  Cabana {cid}")
    lines.append(f"    Escaner : {base}/scan?cab={cid}")
    lines.append(f"    Pedidos : {base}/cabana?cab={cid}&k={key}")
lines.append("")
lines.append("=" * 66)
lines.append(" Tunel temporal: si se reinicia el notebook o se corta el")
lines.append(" proceso, estos enlaces dejan de funcionar. Ejecuta ./run.sh")
lines.append(" nuevamente para generar enlaces nuevos.")
lines.append("=" * 66)
open(links_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

wa = []
wa.append("*DEMO MOTEL - ACCESOS*")
wa.append("Entra desde tu telefono o PC. No pide certificado.")
wa.append("")
wa.append(f"*Menu general:* {base}/")
wa.append(f"*Recepcion:* {base}/recepcion")
wa.append(f"*Cocina:* {base}/kitchen")
wa.append(f"*Panel:* {base}/dashboard")
wa.append(f"*Ingresos:* {base}/ingresos")
wa.append("")
c7 = next((c for c in cabins if c.get("id") == 7), None)
if c7:
    wa.append("*CABANA 7 - TELEFONO DE LA PUERTA*")
    wa.append(f"Escaner: {base}/scan?cab=7")
    wa.append(f"Pedidos: {base}/cabana?cab=7&k={c7.get('scanner_key', '')}")
    wa.append("")
wa.append("*TODAS LAS CABANAS*")
for c in cabins:
    cid = c.get("id")
    key = c.get("scanner_key", "")
    wa.append(f"Cabana {cid}: escaner {base}/scan?cab={cid} | "
              f"pedidos {base}/cabana?cab={cid}&k={key}")
wa.append("")
wa.append("Link temporal de demo. Cualquier duda, avisame.")
open(wa_path, "w", encoding="utf-8").write("\n".join(wa) + "\n")

xlines = list(lines)
xlines.append("")
xlines.append("PERSONAL DEL MOTEL (solo red local)")
xlines.append("-" * 66)
xlines.append(f"  http://{local_ip}:8081/staff")
xlines.append("  (No disponible desde el tunel publico)")
xlines.append("")
xlines.append("Cada codigo QR de personal abre cualquier cabana en cualquier")
xlines.append("momento y queda registrado en los eventos del panel.")
open(x_path, "w", encoding="utf-8").write("\n".join(xlines) + "\n")

print("\n".join(wa))
PY

echo
echo "[demo] Lista completa : $LINKS"
echo "[demo] Mensaje WhatsApp: $WA"
echo "[demo] Archivo listo  : x.txt"
echo "[demo] Tunel activo   : $URL"
echo "[demo] Cerrar tunel   : ./run.sh stop"
