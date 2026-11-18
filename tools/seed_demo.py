#!/usr/bin/env python3
"""Siembra la base de datos con cabanas, dispositivos y productos de demo.

Uso:
    python3 tools/seed_demo.py            # 8 cabanas, dispositivos "virtual"
    python3 tools/seed_demo.py --sim 3    # 3 cabanas apuntan al simulador local
    python3 tools/seed_demo.py --reset    # borra y recrea todo
"""

import argparse
import os
import secrets
import socket
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "server"))

import db  # noqa: E402

CABINS = [
    ("Cabana 1", 15000, 24000, 38000),
    ("Cabana 2", 15000, 24000, 38000),
    ("Cabana 3", 15000, 24000, 38000),
    ("Cabana 4", 15000, 24000, 38000),
    ("Cabana 5", 18000, 28000, 44000),
    ("Cabana 6", 18000, 28000, 44000),
    ("Cabana 7", 22000, 34000, 52000),
    ("Cabana 8", 22000, 34000, 52000),
]

PRODUCTS = [
    ("bebidas", "Coca-Cola 350cc", 2500),
    ("bebidas", "Sprite 350cc", 2500),
    ("bebidas", "Agua mineral 500cc", 1500),
    ("bebidas", "Cerveza lata", 3500),
    ("bebidas", "Jugo natural", 2000),
    ("bebidas", "Bebida energetica", 3500),
    ("comidas", "Sandwich completo", 5500),
    ("comidas", "Pizza personal", 6500),
    ("comidas", "Papas fritas porcion", 3000),
    ("comidas", "Completo italiano", 3500),
    ("comidas", "Empanada de queso", 2500),
    ("desayuno", "Desayuno completo", 8000),
    ("desayuno", "Cafe con leche", 1800),
    ("desayuno", "Tostadas", 2000),
    ("otros", "Helado", 2500),
    ("otros", "Cigarrillos", 4000),
    ("otros", "Preservativos", 1500),
    ("otros", "Kit de aseo", 1200),
]


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="borra la BD y recrea")
    ap.add_argument("--sim", type=int, default=0, metavar="N",
                    help="las primeras N cabanas usan el simulador local "
                         "tools/sim_device.py (puertos 9081+)")
    args = ap.parse_args()

    if args.reset:
        for suffix in ("", "-wal", "-shm"):
            path = db.DB_PATH + suffix
            if os.path.exists(path):
                os.remove(path)
        print("[seed] base de datos borrada")

    db.init()
    con = db.connect()
    try:
        if con.execute("SELECT COUNT(*) AS n FROM cabins").fetchone()["n"]:
            print("[seed] la base ya tiene cabanas. Usa --reset para recrear.")
            return

        dev_rows = []
        for i, (name, p3, p6, p12) in enumerate(CABINS, start=1):
            key = secrets.token_hex(4)
            con.execute(
                "INSERT INTO cabins(name, price_3h, price_6h, price_12h, scanner_key)"
                " VALUES(?,?,?,?,?)", (name, p3, p6, p12, key))
            cabin_id = con.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            dev_id = f"cab{i:02d}"
            secret = secrets.token_hex(16)
            if i <= args.sim:
                ip, port = "127.0.0.1", 9080 + i
            else:
                ip, port = "virtual", 80
            con.execute(
                "INSERT INTO devices(id, kind, cabin_id, ip, port, secret, relay_ms)"
                " VALUES(?,?,?,?,?,?,?)",
                (dev_id, "cabin", cabin_id, ip, port, secret, 1000))
            dev_rows.append((name, cabin_id, key, dev_id, secret))

        gate_secret = secrets.token_hex(16)
        gate_ip, gate_port = ("127.0.0.1", 9099) if args.sim else ("virtual", 80)
        con.execute(
            "INSERT INTO devices(id, kind, cabin_id, ip, port, secret, relay_ms)"
            " VALUES(?,?,?,?,?,?,?)",
            ("gate-01", "gate", None, gate_ip, gate_port, gate_secret, 1500))

        for cat, name, price in PRODUCTS:
            con.execute("INSERT INTO products(name, category, price) VALUES(?,?,?)",
                        (name, cat, price))
        con.commit()
    finally:
        con.close()

    host = local_ip()
    print()
    print("=" * 74)
    print("  Base de datos lista.")
    print("=" * 74)
    print(f"  {'Cabana':<10} {'Escáner (teléfono puerta)':<46} {'Dispositivo':<10}")
    for name, cid, key, dev_id, _ in dev_rows:
        print(f"  {name:<10} /scan?cab={cid}&k={key:<23} {dev_id:<10}")
    print()
    print("  URL completa (para el teléfono):")
    for name, cid, key, _, _ in dev_rows[:2]:
        print(f"    http://{host}:8080/scan?cab={cid}&k={key}")
        print(f"    http://{host}:8080/cabana?cab={cid}&k={key}")
    print()
    print("  Secretos de dispositivos (para firmware include/config.h):")
    for name, _, _, dev_id, secret in dev_rows:
        print(f"    {dev_id:<10} DEVICE_KEY \"{secret}\"")
    print(f"    {'gate-01':<10} DEVICE_KEY \"{gate_secret}\"")
    print()
    if args.sim:
        print(f"  Simuladores listos: arranca con")
        for i in range(1, args.sim + 1):
            print(f"    python3 tools/sim_device.py --id cab{i:02d} --port {9080 + i}")
        print(f"    python3 tools/sim_device.py --id gate-01 --port 9099")
        print()
    print("  Arranca el servidor:  ./start.sh  (o python3 server/app.py)")


if __name__ == "__main__":
    main()
