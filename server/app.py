#!/usr/bin/env python3
"""Servidor central del sistema de moteles (intranet).

Sin dependencias externas: solo la libreria estandar de Python.

Paginas web servidas:
  /            menu de acceso
  /recepcion   mostrador: check-in, cobro, barrera, reimpresion
  /scan        lector QR de la puerta de cada cabana (camara o codigo manual)
  /cabana      catalogo de alimentos/pedidos de la cabana
  /kitchen     pantalla de cocina
  /dashboard   panel de ocupacion en vivo

Flujo principal:
  1. Recepcion registra el ingreso -> genera ticket QR -> imprime -> abre barrera.
  2. El cliente llega a su cabana y presenta el QR al telefono de la puerta.
  3. El telefono consulta al servidor; si todo calza, el servidor ordena por
     WiFi a la NodeMCU ESP8266 de la cabana: rele ON 1 segundo -> chapa abierta.
  4. Boton fisico interior: abre 5 segundos sin autorizacion (salida segura).
  5. Pedidos de alimentos desde el telefono de la cabana -> cocina y cuenta.
  6. Dashboard: ocupacion, tiempos, cargos por servicios en tiempo real.
"""

import datetime as dt
import json
import mimetypes
import os
import secrets
import socket
import ssl
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "server"))

import db          # noqa: E402
import doorctl     # noqa: E402
import printer     # noqa: E402

WEB_DIR = os.path.join(BASE, "server", "web")
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))

QR_PREFIX = "MTL1-"
STAFF_PREFIX = "STAFF-"


# ------------------------------------------------------------------ utilidades

def log(msg):
    stamp = dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def now_dt():
    return dt.datetime.now().replace(microsecond=0)


def iso(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def parse_iso(s):
    return dt.datetime.strptime(str(s), "%Y-%m-%d %H:%M:%S")


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def cabin_by_id(con, cabin_id):
    return con.execute("SELECT * FROM cabins WHERE id=?", (cabin_id,)).fetchone()


def device_for_cabin(con, cabin_id):
    return con.execute(
        "SELECT * FROM devices WHERE kind='cabin' AND cabin_id=?", (cabin_id,)
    ).fetchone()


def gate_device(con):
    return con.execute("SELECT * FROM devices WHERE kind='gate' ORDER BY id LIMIT 1").fetchone()


def _cabin_ok(cabin, key):
    """Con require_keys=false (demo) no se exige la clave de cabana."""
    if not CFG.get("require_keys", False):
        return True
    return bool(key) and key == cabin["scanner_key"]


def unlock_cabin(con, cabin_id, ms=1000):
    dev = device_for_cabin(con, cabin_id)
    if not dev:
        return {"ok": False, "detail": "cabana sin dispositivo registrado"}
    res = doorctl.unlock(dev, ms=ms)
    log(f"UNLOCK cab={cabin_id} -> {res['detail']}")
    return res


def unlock_gate(con, ms=1500):
    dev = gate_device(con)
    if not dev:
        return {"ok": False, "detail": "sin dispositivo de barrera"}
    res = doorctl.unlock(dev, ms=ms)
    log(f"UNLOCK barrera -> {res['detail']}")
    return res


# ------------------------------------------------------------------ consultas

def build_state():
    con = db.connect()
    try:
        now = now_dt()
        cabins = con.execute("SELECT * FROM cabins ORDER BY id").fetchall()
        devs = {d["cabin_id"]: d for d in con.execute(
            "SELECT * FROM devices WHERE kind='cabin'").fetchall()}
        out = {"ok": True, "motel": CFG["motel"]["name"], "ts": iso(now),
               "printer_mode": CFG["printer"].get("mode"),
               "cabins": [], "devices": [], "events": [],
               "totals": {"libres": 0, "ocupadas": 0, "recaudacion": 0.0,
                          "pedidos_pendientes": 0}}
        for c in cabins:
            dev = devs.get(c["id"])
            item = {
                "id": c["id"], "name": c["name"], "state": c["state"],
                "prices": {"180": c["price_3h"], "360": c["price_6h"],
                           "720": c["price_12h"]},
                "scanner_key": c["scanner_key"],
                "device_id": dev["id"] if dev else None,
            }
            if c["state"] == "ocupada" and c["current_ticket_id"]:
                t = con.execute("SELECT * FROM tickets WHERE id=?",
                                (c["current_ticket_id"],)).fetchone()
                charges = con.execute(
                    "SELECT COALESCE(SUM(total),0) AS s FROM orders "
                    "WHERE ticket_id=? AND status!='cancelado'", (t["id"],)
                ).fetchone()["s"]
                item["ticket"] = {
                    "id": t["id"], "issued_at": t["issued_at"],
                    "valid_until": t["valid_until"], "duration_min": t["duration_min"],
                    "price": t["price"], "entry_count": t["entry_count"],
                    "plate": t["plate"], "token_short": t["token_short"],
                }
                item["charges"] = charges
                item["total"] = t["price"] + charges
                item["remaining_min"] = int(
                    (parse_iso(t["valid_until"]) - now).total_seconds() // 60)
                item["elapsed_min"] = int(
                    (now - parse_iso(t["issued_at"])).total_seconds() // 60)
                out["totals"]["ocupadas"] += 1
                out["totals"]["recaudacion"] += item["total"]
            else:
                out["totals"]["libres"] += 1
            out["cabins"].append(item)

        for d in con.execute("SELECT * FROM devices ORDER BY id").fetchall():
            row = {"id": d["id"], "kind": d["kind"], "cabin_id": d["cabin_id"],
                   "ip": d["ip"], "port": d["port"], "last_seen": d["last_seen"],
                   "last_event": d["last_event"]}
            if d["ip"] == "virtual":
                row["online"] = True
                row["status"] = "simulado"
            elif d["last_seen"]:
                age = (now - parse_iso(d["last_seen"])).total_seconds()
                row["online"] = age < 120
                row["status"] = "en linea" if age < 120 else f"sin senal {int(age)}s"
            else:
                row["online"] = False
                row["status"] = "nunca visto"
            out["devices"].append(row)

        evs = con.execute(
            "SELECT e.*, c.name AS cabin_name FROM events e "
            "LEFT JOIN cabins c ON c.id=e.cabin_id ORDER BY e.id DESC LIMIT 80"
        ).fetchall()
        out["events"] = [dict(e) for e in evs]

        pend = con.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE status IN ('nuevo','preparando','listo')"
        ).fetchone()["n"]
        out["totals"]["pedidos_pendientes"] = pend
        return out
    finally:
        con.close()


def kitchen_orders():
    con = db.connect()
    try:
        q = ("SELECT o.*, c.name AS cabin_name FROM orders o "
             "JOIN cabins c ON c.id=o.cabin_id WHERE o.status IN "
             "('nuevo','preparando','listo') ORDER BY o.id ASC")
        active = con.execute(q).fetchall()
        q2 = ("SELECT o.*, c.name AS cabin_name FROM orders o "
              "JOIN cabins c ON c.id=o.cabin_id WHERE o.status='entregado' "
              "ORDER BY o.id DESC LIMIT 6")
        recent = con.execute(q2).fetchall()

        def with_items(o):
            items = con.execute(
                "SELECT name, qty, price FROM order_items WHERE order_id=?",
                (o["id"],)).fetchall()
            d = dict(o)
            d["items"] = [dict(i) for i in items]
            return d

        return {"ok": True,
                "orders": [with_items(o) for o in active] +
                          [with_items(o) for o in recent]}
    finally:
        con.close()


def revenue_data():
    """Ingresos: en curso (instantaneo) y acumulados (dia/mes) + historial."""
    con = db.connect()
    try:
        hoy = now_dt().strftime("%Y-%m-%d")
        mes = now_dt().strftime("%Y-%m")

        def sums(where, args):
            row = con.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS base, "
                "COALESCE(SUM(total_charged - price),0) AS services, "
                "COALESCE(SUM(total_charged),0) AS total "
                "FROM tickets WHERE status='cerrado' AND " + where, args).fetchone()
            return dict(row)

        out = {"ok": True, "hoy": sums("substr(closed_at,1,10)=?", (hoy,)),
               "mes": sums("substr(closed_at,1,7)=?", (mes,))}

        hist = con.execute(
            "SELECT t.id, t.issued_at, t.closed_at, t.duration_min, t.price,"
            " t.total_charged, c.name AS cabin_name FROM tickets t"
            " JOIN cabins c ON c.id=t.cabin_id WHERE t.status='cerrado'"
            " ORDER BY t.closed_at DESC LIMIT 60").fetchall()
        out["historial"] = [dict(h) for h in hist]

        act = con.execute(
            "SELECT t.id, t.issued_at, t.valid_until, t.duration_min, t.price,"
            " c.name AS cabin_name FROM tickets t"
            " JOIN cabins c ON c.id=t.cabin_id WHERE t.status='activo'"
            " ORDER BY t.id").fetchall()
        en_curso, total_curso = [], 0.0
        for a in act:
            serv = con.execute(
                "SELECT COALESCE(SUM(total),0) AS s FROM orders"
                " WHERE ticket_id=? AND status!='cancelado'", (a["id"],)
            ).fetchone()["s"]
            d = dict(a)
            d["services"] = serv
            d["total_now"] = a["price"] + serv
            total_curso += d["total_now"]
            en_curso.append(d)
        out["en_curso"] = en_curso
        out["en_curso_total"] = total_curso

        por_dia = []
        for i in range(13, -1, -1):
            day = (now_dt() - dt.timedelta(days=i)).strftime("%Y-%m-%d")
            row = con.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS base, "
                "COALESCE(SUM(total_charged - price),0) AS services, "
                "COALESCE(SUM(total_charged),0) AS total FROM tickets "
                "WHERE status='cerrado' AND substr(closed_at,1,10)=?", (day,)
            ).fetchone()
            por_dia.append({"dia": day, "n": row["n"], "base": row["base"],
                            "services": row["services"], "total": row["total"]})
        out["por_dia"] = por_dia
        return out
    finally:
        con.close()


def build_xlsx(sheets):
    """Genera un .xlsx minimo sin dependencias. sheets: [(nombre, filas)]."""
    import io
    import zipfile

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    def col(n):
        name = ""
        n += 1
        while n:
            n, rem = divmod(n - 1, 26)
            name = chr(65 + rem) + name
        return name

    def sheet_xml(rows):
        out = []
        for ri, row in enumerate(rows, start=1):
            cells = []
            for ci, val in enumerate(row):
                ref = f"{col(ci)}{ri}"
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    cells.append(f'<c r="{ref}"><v>{val}</v></c>')
                else:
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{esc(val)}</t></is></c>')
            out.append(f'<row r="{ri}">' + "".join(cells) + "</row>")
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<sheetData>" + "".join(out) + "</sheetData></worksheet>")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
        for i in range(1, len(sheets) + 1):
            ct.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType='
                      '"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        ct.append("</Types>")
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   "</Relationships>")
        sheets_xml = "".join(
            f'<sheet name="{esc(name[:31])}" sheetId="{i}" r:id="rId{i}"/>'
            for i, (name, _) in enumerate(sheets, start=1))
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f"<sheets>{sheets_xml}</sheets></workbook>")
        rels = "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(sheets) + 1))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f"{rels}</Relationships>")
        for i, (_, rows) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))
    return buf.getvalue()


def revenue_xlsx(rev):
    resumen = [
        ["Reporte de ingresos - " + CFG["motel"]["name"]],
        ["Generado", iso(now_dt())],
        [],
        ["Periodo", "Salidas", "Base", "Servicios", "Total"],
        ["Hoy", rev["hoy"]["n"], rev["hoy"]["base"], rev["hoy"]["services"], rev["hoy"]["total"]],
        ["Mes", rev["mes"]["n"], rev["mes"]["base"], rev["mes"]["services"], rev["mes"]["total"]],
        ["En curso", len(rev["en_curso"]), "", "", rev["en_curso_total"]],
        [],
        ["Ultimos 14 dias", "Salidas", "Base", "Servicios", "Total"],
    ]
    for d in rev["por_dia"]:
        resumen.append([d["dia"], d["n"], d["base"], d["services"], d["total"]])

    curso = [["Cabana", "Entrada", "Valido hasta", "Minutos", "Base", "Servicios",
              "Total actual"]]
    for t in rev["en_curso"]:
        curso.append([t["cabin_name"], t["issued_at"], t["valid_until"],
                      t["duration_min"], t["price"], t["services"], t["total_now"]])

    cobros = [["#", "Cabana", "Entrada", "Salida", "Minutos", "Base", "Servicios",
               "Total cobrado"]]
    for t in rev["historial"]:
        cobros.append([t["id"], t["cabin_name"], t["issued_at"], t["closed_at"],
                       t["duration_min"], t["price"],
                       (t["total_charged"] or 0) - t["price"], t["total_charged"]])

    return build_xlsx([("Resumen", resumen), ("EnCurso", curso), ("Cobros", cobros)])


def cabin_state(cab_id, key):
    con = db.connect()
    try:
        cabin = cabin_by_id(con, cab_id)
        if not cabin or not _cabin_ok(cabin, key):
            return None
        data = {"ok": True, "cabin": {"id": cabin["id"], "name": cabin["name"]},
                "state": cabin["state"], "ticket": None, "charges": 0.0,
                "orders": []}
        if cabin["current_ticket_id"]:
            t = con.execute("SELECT * FROM tickets WHERE id=?",
                            (cabin["current_ticket_id"],)).fetchone()
            data["ticket"] = {"valid_until": t["valid_until"],
                              "duration_min": t["duration_min"],
                              "price": t["price"], "entry_count": t["entry_count"]}
            data["charges"] = con.execute(
                "SELECT COALESCE(SUM(total),0) AS s FROM orders "
                "WHERE ticket_id=? AND status!='cancelado'", (t["id"],)
            ).fetchone()["s"]
        orders = con.execute(
            "SELECT * FROM orders WHERE cabin_id=? ORDER BY id DESC LIMIT 10",
            (cab_id,)).fetchall()
        for o in orders:
            d = dict(o)
            items = con.execute(
                "SELECT name, qty, price FROM order_items WHERE order_id=?",
                (o["id"],)).fetchall()
            d["items"] = [dict(i) for i in items]
            data["orders"].append(d)
        return data
    finally:
        con.close()


# ------------------------------------------------------------------ negocios

def do_checkin(cabin_id, duration_min, plate):
    con = db.connect()
    try:
        cabin = cabin_by_id(con, cabin_id)
        if not cabin:
            return 404, {"ok": False, "error": "cabana no existe"}
        if cabin["state"] != "libre":
            return 409, {"ok": False, "error": "cabana ocupada"}
        prices = {180: cabin["price_3h"], 360: cabin["price_6h"], 720: cabin["price_12h"]}
        if duration_min not in prices:
            return 400, {"ok": False, "error": "duracion invalida (180, 360 o 720)"}
        price = prices[duration_min]
        issued = now_dt()
        valid = issued + dt.timedelta(minutes=duration_min)

        token = None
        short = None
        for _ in range(8):
            cand = secrets.token_hex(8)
            cand_short = cand[:6].upper()
            exists = con.execute(
                "SELECT 1 FROM tickets WHERE token=? OR token_short=?",
                (cand, cand_short)).fetchone()
            if not exists:
                token, short = cand, cand_short
                break
        if not token:
            return 500, {"ok": False, "error": "no se pudo generar token"}

        cur = con.execute(
            "INSERT INTO tickets(cabin_id, token, token_short, issued_at, valid_until,"
            " duration_min, price, plate) VALUES(?,?,?,?,?,?,?,?)",
            (cabin_id, token, short, iso(issued), iso(valid), duration_min, price,
             plate or None))
        ticket_id = cur.lastrowid
        con.execute("UPDATE cabins SET state='ocupada', current_ticket_id=? WHERE id=?",
                    (ticket_id, cabin_id))
        db.add_event(con, "checkin", cabin_id=cabin_id,
                     detail=f"ticket #{ticket_id} {printer.dur_label(duration_min)} "
                            f"{printer.fmt_clp(price)}")

        t = {"id": ticket_id, "duration_min": duration_min, "price": price,
             "valid_until": iso(valid), "token": token, "token_short": short}
        payload = QR_PREFIX + token
        text = printer.ticket_text(CFG, t, cabin["name"], payload)
        esc = printer.escpos_ticket(CFG, t, cabin["name"], payload)
        print_res = printer.send(CFG, esc, text, f"ticket_{ticket_id}_{cabin['name']}")

        gate_res = unlock_gate(con, ms=1500)
        db.add_event(con, "barrera", detail="apertura automatica post check-in")
        con.commit()
    finally:
        con.close()

    log(f"CHECKIN cab={cabin_id} ticket=#{ticket_id} {printer.dur_label(duration_min)}")
    return 200, {
        "ok": True,
        "ticket": {"id": ticket_id, "cabin_id": cabin_id, "cabin_name": cabin["name"],
                   "issued_at": iso(issued), "valid_until": iso(valid),
                   "duration_min": duration_min, "price": price,
                   "token_short": short, "plate": plate or None},
        "qr_payload": payload,
        "print": print_res,
        "gate": gate_res,
    }


def do_checkout(cabin_id):
    con = db.connect()
    try:
        cabin = cabin_by_id(con, cabin_id)
        if not cabin or cabin["state"] != "ocupada" or not cabin["current_ticket_id"]:
            return 409, {"ok": False, "error": "cabana no esta ocupada"}
        t = con.execute("SELECT * FROM tickets WHERE id=?",
                        (cabin["current_ticket_id"],)).fetchone()
        charges = con.execute(
            "SELECT COALESCE(SUM(total),0) AS s FROM orders "
            "WHERE ticket_id=? AND status!='cancelado'", (t["id"],)
        ).fetchone()["s"]
        total = t["price"] + charges
        con.execute("UPDATE tickets SET status='cerrado', closed_at=?, total_charged=?"
                    " WHERE id=?", (iso(now_dt()), total, t["id"]))
        con.execute("UPDATE cabins SET state='libre', current_ticket_id=NULL WHERE id=?",
                    (cabin_id,))
        db.add_event(con, "checkout", cabin_id=cabin_id,
                     detail=f"total {printer.fmt_clp(total)} "
                            f"(base {printer.fmt_clp(t['price'])} + servicios "
                            f"{printer.fmt_clp(charges)})")
        gate_res = unlock_gate(con, ms=1500)
        con.commit()
    finally:
        con.close()
    log(f"CHECKOUT cab={cabin_id} total={printer.fmt_clp(total)}")
    return 200, {"ok": True, "cabin": cabin["name"], "base": t["price"],
                 "charges": charges, "total": total, "gate": gate_res}


def do_scan(cabin_id, key, code):
    con = db.connect()
    try:
        cabin = cabin_by_id(con, cabin_id)
        if not cabin or not _cabin_ok(cabin, key):
            return 403, {"ok": False, "error": "clave de cabana invalida"}

        code = (code or "").strip()
        upper = code.upper()

        def deny(reason, cabin_match=True):
            db.add_event(con, "scan_denegado", cabin_id=cabin_id,
                         detail=f"{reason} (codigo={code[:24]})")
            con.commit()
            log(f"SCAN DENEGADO cab={cabin_id}: {reason}")
            return 200, {"ok": False, "reason": reason,
                         "cabin": cabin["name"], "cabin_match": cabin_match}

        # --- personal del motel: abre cualquier cabana, en cualquier momento ---
        staff = None
        if upper.startswith(STAFF_PREFIX):
            staff = con.execute(
                "SELECT * FROM staff WHERE active=1 AND token=?",
                (upper[len(STAFF_PREFIX):].lower(),)).fetchone()
            if not staff:
                return deny("Codigo de personal no reconocido")
        elif len(upper) == 6:
            staff = con.execute(
                "SELECT * FROM staff WHERE active=1 AND token_short=?",
                (upper,)).fetchone()
        elif len(upper) == 16:
            staff = con.execute(
                "SELECT * FROM staff WHERE active=1 AND token=?",
                (upper.lower(),)).fetchone()

        if staff:
            unlock = unlock_cabin(con, cabin_id, ms=1000)
            db.add_event(con, "staff_access", cabin_id=cabin_id,
                         detail=f"{staff['name']} ({staff['role']}) en {cabin['name']}")
            db.add_event(con, "puerta", cabin_id=cabin_id,
                         detail=f"apertura por QR de personal ({unlock['detail'][:90]})")
            con.commit()
            log(f"STAFF OK cab={cabin_id} staff={staff['name']}")
            return 200, {"ok": True, "cabin": cabin["name"],
                         "staff": {"id": staff["id"], "name": staff["name"],
                                   "role": staff["role"]},
                         "staff_access": True, "unlock": unlock}

        token = None
        if upper.startswith(QR_PREFIX):
            token = upper[len(QR_PREFIX):].lower()
        elif len(upper) == 6:
            row = con.execute(
                "SELECT token FROM tickets WHERE token_short=? AND status='activo'",
                (upper,)).fetchone()
            token = row["token"] if row else None
        elif len(upper) == 16:
            token = upper.lower()

        t = con.execute("SELECT * FROM tickets WHERE token=?",
                        (token,)).fetchone() if token else None

        if not t:
            return deny("Codigo no reconocido")
        if t["cabin_id"] != cabin["id"]:
            otra = cabin_by_id(con, t["cabin_id"])["name"]
            return deny(f"Ticket de {otra}, pero este lector es de {cabin['name']}",
                        cabin_match=False)
        if t["status"] == "cerrado":
            return deny("Ticket cerrado (estadia finalizada)")
        now = now_dt()
        if now > parse_iso(t["valid_until"]):
            con.execute("UPDATE tickets SET status='vencido' WHERE id=?", (t["id"],))
            return deny("Ticket vencido")
        if CFG.get("qr_policy") == "one_time" and t["entry_count"] > 0:
            return deny("Ticket ya utilizado")

        first = t["first_entry_at"] or iso(now)
        con.execute("UPDATE tickets SET entry_count=entry_count+1, first_entry_at=?"
                    " WHERE id=?", (first, t["id"]))
        db.add_event(con, "scan_ok", cabin_id=cabin_id,
                     detail=f"ticket #{t['id']} entrada #{t['entry_count'] + 1}")
        unlock = unlock_cabin(con, cabin_id, ms=1000)
        db.add_event(con, "puerta", cabin_id=cabin_id,
                     detail=f"apertura por QR ({unlock['detail'][:90]})")
        con.commit()
    finally:
        con.close()
    log(f"SCAN OK cab={cabin_id} ticket=#{t['id']}")
    return 200, {"ok": True, "cabin": cabin["name"],
                 "valid_until": t["valid_until"], "price": t["price"],
                 "entries": t["entry_count"] + 1, "unlock": unlock}


def do_order(cabin_id, key, items):
    con = db.connect()
    try:
        cabin = cabin_by_id(con, cabin_id)
        if not cabin or not _cabin_ok(cabin, key):
            return 403, {"ok": False, "error": "clave de cabana invalida"}
        if cabin["state"] != "ocupada":
            return 409, {"ok": False, "error": "cabana no ocupada"}
        if not items:
            return 400, {"ok": False, "error": "pedido vacio"}
        rows, total = [], 0.0
        for it in items:
            pid = int(it.get("product_id", 0))
            qty = max(1, min(20, int(it.get("qty", 1))))
            p = con.execute("SELECT * FROM products WHERE id=? AND active=1",
                            (pid,)).fetchone()
            if not p:
                return 400, {"ok": False, "error": f"producto {pid} no existe"}
            rows.append((p, qty))
            total += p["price"] * qty
        cur = con.execute("INSERT INTO orders(cabin_id, ticket_id, total) VALUES(?,?,?)",
                          (cabin_id, cabin["current_ticket_id"], total))
        oid = cur.lastrowid
        for p, qty in rows:
            con.execute("INSERT INTO order_items(order_id, product_id, name, qty, price)"
                        " VALUES(?,?,?,?,?)", (oid, p["id"], p["name"], qty, p["price"]))
        db.add_event(con, "pedido", cabin_id=cabin_id,
                     detail=f"orden #{oid} {printer.fmt_clp(total)}")
        con.commit()
    finally:
        con.close()
    log(f"PEDIDO cab={cabin_id} orden=#{oid} {printer.fmt_clp(total)}")
    return 200, {"ok": True, "order_id": oid, "total": total}


def do_order_status(order_id, status):
    allowed = ("nuevo", "preparando", "listo", "entregado", "cancelado")
    if status not in allowed:
        return 400, {"ok": False, "error": "estado invalido"}
    con = db.connect()
    try:
        o = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            return 404, {"ok": False, "error": "orden no existe"}
        con.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        if status in ("entregado", "cancelado"):
            db.add_event(con, "pedido_estado", cabin_id=o["cabin_id"],
                         detail=f"orden #{order_id} -> {status}")
        con.commit()
    finally:
        con.close()
    return 200, {"ok": True, "order_id": order_id, "status": status}


def do_reprint(cabin_id):
    con = db.connect()
    try:
        cabin = cabin_by_id(con, cabin_id)
        if not cabin:
            return 404, {"ok": False, "error": "cabana no existe"}
        t = con.execute("SELECT * FROM tickets WHERE cabin_id=? ORDER BY id DESC LIMIT 1",
                        (cabin_id,)).fetchone()
        if not t:
            return 404, {"ok": False, "error": "sin tickets para esa cabana"}
        payload = QR_PREFIX + t["token"]
        text = printer.ticket_text(CFG, t, cabin["name"], payload)
        esc = printer.escpos_ticket(CFG, t, cabin["name"], payload)
        res = printer.send(CFG, esc, text, f"reimpresion_{t['id']}_{cabin['name']}")
        db.add_event(con, "reimpresion", cabin_id=cabin_id, detail=f"ticket #{t['id']}")
        con.commit()
    finally:
        con.close()
    return 200, {"ok": True, "qr_payload": payload,
                 "token_short": t["token_short"], "print": res}


# ------------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "MotelServer/1.0"

    # ---------- helpers ----------
    def log_message(self, fmt, *args):  # silenciar log por defecto
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _err(self, code, msg):
        self._json({"ok": False, "error": msg}, code)

    def _panel_ok(self):
        if not CFG.get("require_keys", False):
            return True
        key = self.headers.get("X-Panel-Key", "")
        expected = CFG.get("panel_key", "")
        import hmac as _hmac
        return bool(key) and _hmac.compare_digest(key, expected)

    def _is_public_tunnel(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host.endswith(".trycloudflare.com")

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _static(self, path):
        if path == "/":
            rel = "index.html"
        elif os.path.splitext(path)[1]:
            rel = path.lstrip("/")
        else:
            rel = path.strip("/") + ".html"
        fp = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not fp.startswith(WEB_DIR) or not os.path.isfile(fp):
            return self._err(404, f"no encontrado: {path}")
        with open(fp, "rb") as fh:
            data = fh.read()
        ctype = mimetypes.guess_type(fp)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",
                                                  "application/json"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---------- GET ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            if path.startswith("/api/"):
                if path == "/api/config":
                    return self._json({"ok": True, "motel": CFG["motel"]["name"],
                                       "require_keys": bool(CFG.get("require_keys", False))})
                if path == "/api/state":
                    if not self._panel_ok():
                        return self._err(401, "clave de panel requerida")
                    return self._json(build_state())
                if path == "/api/products":
                    con = db.connect()
                    try:
                        rows = con.execute(
                            "SELECT * FROM products WHERE active=1 ORDER BY category, name"
                        ).fetchall()
                        return self._json({"ok": True,
                                           "products": [dict(r) for r in rows]})
                    finally:
                        con.close()
                if path == "/api/cabins":
                    con = db.connect()
                    try:
                        rows = con.execute(
                            "SELECT id, name FROM cabins ORDER BY id"
                        ).fetchall()
                        return self._json({"ok": True,
                                           "cabins": [dict(r) for r in rows]})
                    finally:
                        con.close()
                if path == "/api/staff":
                    if self._is_public_tunnel():
                        return self._err(403, "personal solo en red local")
                    if not self._panel_ok():
                        return self._err(401, "clave de panel requerida")
                    con = db.connect()
                    try:
                        rows = con.execute(
                            "SELECT id, name, role, token, token_short FROM staff"
                            " WHERE active=1 ORDER BY id").fetchall()
                        staff = [{"id": r["id"], "name": r["name"], "role": r["role"],
                                  "payload": STAFF_PREFIX + r["token"],
                                  "short": r["token_short"]} for r in rows]
                        return self._json({"ok": True, "staff": staff})
                    finally:
                        con.close()
                if path == "/api/cabin_state":
                    try:
                        cab = int(qs.get("cab", ["0"])[0])
                    except ValueError:
                        return self._err(400, "cab invalido")
                    key = qs.get("k", [""])[0]
                    data = cabin_state(cab, key)
                    if data is None:
                        return self._err(403, "clave de cabana invalida")
                    return self._json(data)
                if path == "/api/orders":
                    if not self._panel_ok():
                        return self._err(401, "clave de panel requerida")
                    return self._json(kitchen_orders())
                if path == "/api/revenue":
                    if not self._panel_ok():
                        return self._err(401, "clave de panel requerida")
                    return self._json(revenue_data())
                if path == "/api/revenue/export.xlsx":
                    import hmac as _hmac
                    key = self.headers.get("X-Panel-Key", "") or qs.get("k", [""])[0]
                    ok = (not CFG.get("require_keys", False)) or (
                        bool(key) and _hmac.compare_digest(key, CFG.get("panel_key", "")))
                    if not ok:
                        return self._err(401, "clave de panel requerida")
                    data = revenue_xlsx(revenue_data())
                    fname = "ingresos_" + now_dt().strftime("%Y%m%d_%H%M") + ".xlsx"
                    self.send_response(200)
                    self.send_header("Content-Type",
                                     "application/vnd.openxmlformats-officedocument"
                                     ".spreadsheetml.sheet")
                    self.send_header("Content-Disposition",
                                     f'attachment; filename="{fname}"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return self._err(404, "ruta api no existe")

            if path in ("/staff", "/staff.html") and self._is_public_tunnel():
                return self._err(403, "pagina de personal solo en red local")
            return self._static(path)
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            log(f"ERROR GET {path}: {exc!r}")
            try:
                self._err(500, str(exc))
            except Exception:  # noqa: BLE001
                pass

    # ---------- POST ----------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._body()
        try:
            if path == "/api/checkin":
                if not self._panel_ok():
                    return self._err(401, "clave de panel requerida")
                try:
                    cabin_id = int(body.get("cabin_id", 0))
                    duration = int(body.get("duration_min", 0))
                except (TypeError, ValueError):
                    return self._err(400, "parametros invalidos")
                code, resp = do_checkin(cabin_id, duration, body.get("plate"))
                return self._json(resp, code)

            if path == "/api/checkout":
                if not self._panel_ok():
                    return self._err(401, "clave de panel requerida")
                code, resp = do_checkout(int(body.get("cabin_id", 0)))
                return self._json(resp, code)

            if path == "/api/scan":
                try:
                    cab = int(body.get("cab", 0))
                except (TypeError, ValueError):
                    return self._err(400, "cab invalido")
                code, resp = do_scan(cab, body.get("k", ""), body.get("code", ""))
                return self._json(resp, code)

            if path == "/api/orders":
                try:
                    cab = int(body.get("cab", 0))
                except (TypeError, ValueError):
                    return self._err(400, "cab invalido")
                code, resp = do_order(cab, body.get("k", ""), body.get("items") or [])
                return self._json(resp, code)

            if path == "/api/orders/status":
                if not self._panel_ok():
                    return self._err(401, "clave de panel requerida")
                code, resp = do_order_status(int(body.get("order_id", 0)),
                                             body.get("status", ""))
                return self._json(resp, code)

            if path == "/api/panel/open":
                if not self._panel_ok():
                    return self._err(401, "clave de panel requerida")
                cabin_id = int(body.get("cabin_id", 0))
                con = db.connect()
                try:
                    res = unlock_cabin(con, cabin_id, ms=1000)
                    db.add_event(con, "puerta", cabin_id=cabin_id,
                                 detail=f"apertura manual mostrador ({res['detail'][:80]})")
                    con.commit()
                finally:
                    con.close()
                return self._json({"ok": res["ok"], "unlock": res})

            if path == "/api/gate/open":
                if not self._panel_ok():
                    return self._err(401, "clave de panel requerida")
                con = db.connect()
                try:
                    res = unlock_gate(con, ms=1500)
                    db.add_event(con, "barrera", detail="apertura manual mostrador")
                    con.commit()
                finally:
                    con.close()
                return self._json({"ok": res["ok"], "unlock": res})

            if path == "/api/exit_request":
                try:
                    cab = int(body.get("cab", 0))
                except (TypeError, ValueError):
                    return self._err(400, "cab invalido")
                con = db.connect()
                try:
                    cabin = cabin_by_id(con, cab)
                    if not cabin or not _cabin_ok(cabin, body.get("k", "")):
                        return self._err(403, "clave de cabana invalida")
                    res = unlock_cabin(con, cab, ms=5000)
                    db.add_event(con, "salida", cabin_id=cab,
                                 detail=f"boton salida app ({res['detail'][:80]})")
                    con.commit()
                finally:
                    con.close()
                return self._json({"ok": res["ok"], "unlock": res})

            if path == "/api/reprint":
                if not self._panel_ok():
                    return self._err(401, "clave de panel requerida")
                code, resp = do_reprint(int(body.get("cabin_id", 0)))
                return self._json(resp, code)

            if path == "/api/devices/heartbeat":
                device_id = body.get("device_id", "")
                con = db.connect()
                try:
                    dev = con.execute("SELECT * FROM devices WHERE id=?",
                                      (device_id,)).fetchone()
                    if not dev:
                        return self._err(404, "dispositivo no registrado")
                    canonical = f"{device_id}:heartbeat"
                    ok, why = doorctl.verify(dev["secret"], canonical,
                                             self.headers.get("X-Signature", ""))
                    if not ok:
                        return self._err(401, f"firma invalida ({why})")
                    con.execute("UPDATE devices SET last_seen=?, last_event=? WHERE id=?",
                                (iso(now_dt()), body.get("status", "online"), device_id))
                    con.commit()
                finally:
                    con.close()
                return self._json({"ok": True})

            if path == "/api/devices/event":
                device_id = body.get("device_id", "")
                event = body.get("event", "")
                n = body.get("n", "")
                con = db.connect()
                try:
                    dev = con.execute("SELECT * FROM devices WHERE id=?",
                                      (device_id,)).fetchone()
                    if not dev:
                        return self._err(404, "dispositivo no registrado")
                    canonical = f"{device_id}:event:{event}:{n}"
                    ok, why = doorctl.verify(dev["secret"], canonical,
                                             self.headers.get("X-Signature", ""))
                    if not ok:
                        return self._err(401, f"firma invalida ({why})")
                    con.execute("UPDATE devices SET last_seen=?, last_event=? WHERE id=?",
                                (iso(now_dt()), event, device_id))
                    db.add_event(con, f"dispositivo:{event}", device_id=device_id,
                                 cabin_id=dev["cabin_id"],
                                 detail=f"ms={body.get('ms', '')}")
                    con.commit()
                finally:
                    con.close()
                log(f"EVENTO DISPOSITIVO {device_id}: {event}")
                return self._json({"ok": True})

            return self._err(404, "ruta api no existe")
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            log(f"ERROR POST {path}: {exc!r}")
            try:
                self._err(500, str(exc))
            except Exception:  # noqa: BLE001
                pass


def main():
    db.init()
    host = CFG["server"]["host"]
    port = int(CFG["server"]["port"])
    httpd = ThreadingHTTPServer((host, port), Handler)
    scheme = "http"
    if CFG["server"].get("https"):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(os.path.join(BASE, CFG["server"]["cert"]),
                            os.path.join(BASE, CFG["server"]["key"]))
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    ip = local_ip()
    base = f"{scheme}://{ip}:{port}"
    http_port = int(CFG["server"].get("http_port") or 0)
    if http_port and http_port != port:
        try:
            aux = ThreadingHTTPServer((host, http_port), Handler)
            threading.Thread(target=aux.serve_forever, daemon=True).start()
        except OSError as exc:
            log(f"AVISO: no se pudo abrir HTTP sin certificado en {http_port}: {exc}")
            http_port = 0
    print("=" * 62)
    print(f"  {CFG['motel']['name']} - servidor central")
    print("=" * 62)
    print(f"  Recepcion : {base}/recepcion")
    print(f"  Escaner   : {base}/scan?cab=1&k=<clave de la cabana>")
    print(f"  Cabana    : {base}/cabana?cab=1&k=<clave de la cabana>")
    print(f"  Cocina    : {base}/kitchen")
    print(f"  Panel     : {base}/dashboard")
    if http_port:
        hbase = f"http://{ip}:{http_port}"
        print(f"  Sin cert  : {hbase}/recepcion")
        print(f"  Escaner   : {hbase}/scan?cab=1&k=<clave de la cabana>")
        print(f"  Cabana    : {hbase}/cabana?cab=1&k=<clave de la cabana>")
    print(f"  Impresora : modo '{CFG['printer'].get('mode')}'")
    print("=" * 62)
    log("servidor iniciado")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("servidor detenido")


if __name__ == "__main__":
    main()
