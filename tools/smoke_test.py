#!/usr/bin/env python3
"""Prueba end-to-end del flujo completo contra el servidor local.

Con el servidor corriendo (./start.sh), ejecutar:
    python3 tools/smoke_test.py

Recorre: check-in -> ticket QR -> escaneo OK -> escaneo cruzado y falso ->
pedido -> cocina -> panel -> checkout. Muestra PASS/FAIL de cada paso.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
ROOT = f"http://127.0.0.1:{CFG['server']['port']}"
PK = CFG["panel_key"]

FAILS = []

CFG_KEYS = None  # se completa con /api/config


def call(path, body=None, panel=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(ROOT + path, data=data,
                                 method="POST" if body is not None else "GET")
    req.add_header("Content-Type", "application/json")
    if panel:
        req.add_header("X-Panel-Key", PK)
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except ValueError:
            return {"ok": False, "error": f"HTTP {e.code}"}


def page_ok(path):
    try:
        with urllib.request.urlopen(ROOT + path, timeout=6) as r:
            return r.status == 200 and len(r.read()) > 100
    except Exception:  # noqa: BLE001
        return False


def check(cond, label, extra=""):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {label}" + (f"  ({extra})" if extra else ""))
    if not cond:
        FAILS.append(label)


print("=" * 66)
print("  SMOKE TEST - flujo completo del sistema de moteles")
print("=" * 66)

CFG_KEYS = call("/api/config").get("require_keys", False)
print(f"\n[i] Modo de claves: require_keys={CFG_KEYS}")

# 0. paginas
print("\n[0] Paginas web")
for path in ["/", "/recepcion", "/scan?cab=1&k=x", "/cabana?cab=1&k=x",
             "/kitchen", "/dashboard", "/style.css",
             "/vendor/jsQR.js", "/vendor/qrcode.js"]:
    check(page_ok(path), f"GET {path}")

# 1. estado inicial
print("\n[1] Estado inicial")
st = call("/api/state", panel=True)
check(st.get("ok"), "panel /api/state responde")
libre = next((c for c in st["cabins"] if c["state"] == "libre"), None)
otra = next((c for c in st["cabins"] if c["state"] == "libre" and c is not libre), None)
check(libre is not None and otra is not None, "hay al menos 2 cabanas libres")

# 2. check-in
print("\n[2] Check-in (recepcion registra el ingreso)")
ck = call("/api/checkin",
          {"cabin_id": libre["id"], "duration_min": 180, "plate": "TEST12"},
          panel=True)
check(ck.get("ok"), f"check-in {libre['name']}", str(ck.get("error", "")))
payload = ck.get("qr_payload", "")
check(payload.startswith("MTL1-"), "QR generado", payload[:12] + "...")
short = ck["ticket"]["token_short"]
check(ck["print"].get("ok"), "ticket enviado a impresora",
      str(ck["print"].get("mode")) + ": " + str(ck["print"].get("detail"))[:48])
check(ck.get("gate", {}).get("ok"), "barrera abierta automaticamente",
      str(ck.get("gate", {}).get("detail"))[:48])

# 3. escaneo correcto
print("\n[3] Escaneo del QR en la puerta")
sc = call("/api/scan", {"cab": libre["id"], "k": libre["scanner_key"],
                        "code": payload})
check(sc.get("ok"), "QR correcto abre la cabana",
      str(sc.get("unlock", {}).get("detail"))[:48])
check(sc.get("entries") == 1, "contador de entradas = 1")

sc2 = call("/api/scan", {"cab": libre["id"], "k": libre["scanner_key"],
                         "code": short})
check(sc2.get("ok"), "codigo manual de 6 caracteres tambien funciona")

# 4. intentos invalidos
print("\n[4] Intentos invalidos (anti-fraude)")
sc3 = call("/api/scan", {"cab": otra["id"], "k": otra["scanner_key"],
                         "code": payload})
check(not sc3.get("ok"), "ticket presentado en OTRA cabana es rechazado",
      sc3.get("reason", ""))
sc4 = call("/api/scan", {"cab": libre["id"], "k": libre["scanner_key"],
                         "code": "MTL1-0000000000000000"})
check(not sc4.get("ok"), "codigo inventado es rechazado", sc4.get("reason", ""))
if CFG_KEYS:
    sc5 = call("/api/scan", {"cab": libre["id"], "k": "clave-mala", "code": payload})
    check(not sc5.get("ok"), "clave de cabana incorrecta es rechazada")
else:
    print("  [SKIP] clave de cabana incorrecta es rechazada (require_keys=false)")

# 5. pedido de alimentos
print("\n[5] Pedido de alimentos desde la cabana")
prods = call("/api/products")["products"]
p1, p2 = prods[0], prods[len(prods) // 2]
order = call("/api/orders", {"cab": libre["id"], "k": libre["scanner_key"],
                             "items": [{"product_id": p1["id"], "qty": 2},
                                       {"product_id": p2["id"], "qty": 1}]})
check(order.get("ok"), f"pedido enviado ({p1['name']} x2, {p2['name']} x1)",
      f"total ${order.get('total', 0):,.0f}".replace(",", "."))
esperado = p1["price"] * 2 + p2["price"]
check(order.get("total") == esperado, "total del pedido correcto")

kit = call("/api/orders", panel=True)
check(kit.get("ok") and any(o["id"] == order["order_id"] for o in kit["orders"]),
      "el pedido aparece en cocina")

cs = call(f"/api/cabin_state?cab={libre['id']}&k={libre['scanner_key']}")
check(cs.get("ok") and cs.get("charges") == esperado,
      "cargo reflejado en la cuenta de la cabana")

# 6. panel en vivo
print("\n[6] Panel de ocupacion")
st2 = call("/api/state", panel=True)
cab = next(c for c in st2["cabins"] if c["id"] == libre["id"])
check(cab["state"] == "ocupada", "cabana figura ocupada")
check(cab["charges"] == esperado and cab["total"] == cab["ticket"]["price"] + esperado,
      "base + servicios suman bien en el panel")
tipos = {e["kind"] for e in st2["events"]}
check({"checkin", "scan_ok", "pedido"} <= tipos, "eventos registrados en bitacora")

# 7. checkout
print("\n[7] Salida / cobro")
co = call("/api/checkout", {"cabin_id": libre["id"]}, panel=True)
check(co.get("ok"), "checkout realizado",
      f"total ${co.get('total', 0):,.0f}".replace(",", "."))
check(co.get("total") == cab["ticket"]["price"] + esperado,
      "total = base + servicios")
st3 = call("/api/state", panel=True)
cab3 = next(c for c in st3["cabins"] if c["id"] == libre["id"])
check(cab3["state"] == "libre", "cabana vuelve a estar libre")

# 8. scan despues del cierre
sc6 = call("/api/scan", {"cab": libre["id"], "k": libre["scanner_key"],
                         "code": payload})
check(not sc6.get("ok"), "el ticket cerrado ya no abre", sc6.get("reason", ""))
sc7 = call("/api/scan", {"cab": libre["id"], "k": libre["scanner_key"],
                         "code": short})
check(not sc7.get("ok"), "el codigo manual del ticket cerrado tampoco abre")

print("\n" + "=" * 66)
if FAILS:
    print(f"  RESULTADO: {len(FAILS)} FALLOS")
    for f in FAILS:
        print("   - " + f)
    sys.exit(1)
print("  RESULTADO: TODO OK - flujo completo verificado")
