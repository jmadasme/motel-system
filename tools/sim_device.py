#!/usr/bin/env python3
"""Simula una placa NodeMCU ESP8266 en el PC.

Reproduce EXACTAMENTE el mismo protocolo que el firmware real:
  - /unlock?ms=N&r=nonce  con headers X-Timestamp y X-Signature
    (firma = HMAC-SHA256(secret, "<ts>:<ms>:<r>"))
  - anti-replay
  - /status
  - /sim/exit     simula el boton interior (abre 5 s y avisa al servidor)
  - /sim/heartbeat  fuerza un heartbeat

El secreto se lee de la base de datos si no se pasa --key.

Uso:
    python3 tools/sim_device.py --id cab01 --port 9081
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "server"))

import db  # noqa: E402

ARGS = None
STATE = {"relay": False, "last": "-", "boot": time.time()}
REPLAY = []


def sign(secret, canonical):
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def post_signed(path, canonical, body):
    url = f"http://{ARGS.server_host}:{ARGS.server_port}{path}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "X-Signature": sign(ARGS.key, canonical)},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.read().decode(errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"ERROR {exc}"


def notify(kind):
    if kind == "exit":
        n = int(time.time() * 1000) % 1000000
        body = {"device_id": ARGS.id, "event": "exit_button", "ms": 5000, "n": n}
        canonical = f"{ARGS.id}:event:exit_button:{n}"
    else:
        body = {"device_id": ARGS.id, "status": "online-sim",
                "fw": "sim-1.0", "uptime": int(time.time() - STATE["boot"])}
        canonical = f"{ARGS.id}:heartbeat"
    resp = post_signed("/api/devices/heartbeat" if kind == "hb"
                       else "/api/devices/event", canonical, body)
    print(f"[SIM {ARGS.id}] {kind} -> {resp[:80]}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path == "/unlock":
            ts = self.headers.get("X-Timestamp", "")
            sig = self.headers.get("X-Signature", "")
            r = q.get("r", [""])[0]
            try:
                ms = int(q.get("ms", ["1000"])[0])
            except ValueError:
                ms = 1000
            ms = max(200, min(ms, 15000))
            canonical = f"{ts}:{ms}:{r}"
            if not ts or sig != sign(ARGS.key, canonical):
                print(f"[SIM {ARGS.id}] DENEGADO firma invalida")
                return self._json({"ok": False, "error": "firma invalida"}, 401)
            if canonical in REPLAY:
                print(f"[SIM {ARGS.id}] DENEGADO replay")
                return self._json({"ok": False, "error": "comando repetido"}, 401)
            REPLAY.append(canonical)
            del REPLAY[:-16]
            STATE["relay"] = True
            STATE["last"] = f"remoto {ms}ms"
            print(f"[SIM {ARGS.id}] 🔓 RELE ON {ms} ms   (apertura QR)")
            # apagado simulado
            print(f"[SIM {ARGS.id}] 🔒 RELE OFF")
            STATE["relay"] = False
            notify("exit" if ms >= 3000 else "hb")
            return self._json({"ok": True, "ms": ms, "sim": True})

        if u.path == "/status":
            return self._json({"ok": True, "device_id": ARGS.id, "sim": True,
                               "relay": STATE["relay"], "last": STATE["last"],
                               "uptime": int(time.time() - STATE["boot"])})

        if u.path == "/sim/exit":
            STATE["last"] = "boton_salida 5000ms"
            print(f"[SIM {ARGS.id}] 🚪 BOTON SALIDA -> RELE ON 5000 ms")
            notify("exit")
            return self._json({"ok": True})

        if u.path == "/sim/heartbeat":
            notify("hb")
            return self._json({"ok": True})

        return self._json({"ok": False, "error": "ruta no existe"}, 404)

    def do_POST(self):
        self.do_GET()


def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id", required=True, help="device_id (ej: cab01)")
    ap.add_argument("--port", type=int, default=9081)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--key", help="secreto del dispositivo (default: leer de la BD)")
    ap.add_argument("--server-host", default="127.0.0.1")
    ap.add_argument("--server-port", type=int, default=8080)
    ARGS = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    if not ARGS.key:
        con = db.connect()
        row = con.execute("SELECT secret FROM devices WHERE id=?", (ARGS.id,)).fetchone()
        con.close()
        if not row:
            print(f"[SIM] no existe el dispositivo {ARGS.id} en la BD; "
                  f"pasa --key o siembra con tools/seed_demo.py")
            sys.exit(1)
        ARGS.key = row["secret"]

    print(f"[SIM {ARGS.id}] escuchando en http://{ARGS.host}:{ARGS.port} "
          f"(servidor {ARGS.server_host}:{ARGS.server_port})")
    ThreadingHTTPServer((ARGS.host, ARGS.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
