"""Capa de datos del sistema (SQLite, sin dependencias externas).

Todas las tablas del sistema viven aqui. El servidor central (app.py) y las
herramientas (seed_demo.py, sim_device.py) comparten este modulo.
"""

import os
import secrets
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "motel.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cabins (
  id                INTEGER PRIMARY KEY,
  name              TEXT UNIQUE NOT NULL,
  price_3h          REAL NOT NULL DEFAULT 0,
  price_6h          REAL NOT NULL DEFAULT 0,
  price_12h         REAL NOT NULL DEFAULT 0,
  scanner_key       TEXT NOT NULL,
  state             TEXT NOT NULL DEFAULT 'libre',
  current_ticket_id INTEGER
);
CREATE TABLE IF NOT EXISTS devices (
  id          TEXT PRIMARY KEY,
  kind        TEXT NOT NULL,                    -- 'cabin' | 'gate'
  cabin_id    INTEGER,
  ip          TEXT NOT NULL DEFAULT 'virtual',  -- 'virtual' = simulado por el servidor
  port        INTEGER NOT NULL DEFAULT 80,
  secret      TEXT NOT NULL,
  relay_ms    INTEGER NOT NULL DEFAULT 1000,
  last_seen   TEXT,
  last_event  TEXT
);
CREATE TABLE IF NOT EXISTS tickets (
  id             INTEGER PRIMARY KEY,
  cabin_id       INTEGER NOT NULL,
  token          TEXT UNIQUE NOT NULL,
  token_short    TEXT UNIQUE NOT NULL,
  issued_at      TEXT NOT NULL,
  valid_until    TEXT NOT NULL,
  duration_min   INTEGER NOT NULL,
  price          REAL NOT NULL,
  plate          TEXT,
  status         TEXT NOT NULL DEFAULT 'activo',  -- activo | cerrado | vencido
  entry_count    INTEGER NOT NULL DEFAULT 0,
  first_entry_at TEXT,
  closed_at      TEXT,
  total_charged  REAL
);
CREATE TABLE IF NOT EXISTS staff (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  role        TEXT NOT NULL DEFAULT 'Personal',
  token       TEXT UNIQUE NOT NULL,
  token_short TEXT UNIQUE NOT NULL,
  active      INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS events (
  id        INTEGER PRIMARY KEY,
  ts        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  kind      TEXT NOT NULL,
  cabin_id  INTEGER,
  device_id TEXT,
  detail    TEXT
);
CREATE TABLE IF NOT EXISTS products (
  id       INTEGER PRIMARY KEY,
  name     TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'otros',
  price    REAL NOT NULL,
  active   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS orders (
  id         INTEGER PRIMARY KEY,
  cabin_id   INTEGER NOT NULL,
  ticket_id  INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  status     TEXT NOT NULL DEFAULT 'nuevo',  -- nuevo|preparando|listo|entregado|cancelado
  total      REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS order_items (
  id         INTEGER PRIMARY KEY,
  order_id   INTEGER NOT NULL,
  product_id INTEGER,
  name       TEXT,
  qty        INTEGER NOT NULL,
  price      REAL NOT NULL
);

-- ===================== VISTAS DE CONSULTA =====================

-- Ventas del dia (salidas cobradas hoy)
CREATE VIEW IF NOT EXISTS v_ventas_dia AS
SELECT t.id AS ticket, c.name AS cabana,
       t.issued_at AS entrada, t.closed_at AS salida,
       t.duration_min AS minutos,
       t.price AS base,
       round(COALESCE(t.total_charged, 0) - t.price, 0) AS servicios,
       COALESCE(t.total_charged, 0) AS total
FROM tickets t JOIN cabins c ON c.id = t.cabin_id
WHERE t.status = 'cerrado' AND date(t.closed_at) = date('now', 'localtime')
ORDER BY t.closed_at;

-- Ventas del mes en curso (una fila por salida)
CREATE VIEW IF NOT EXISTS v_ventas_mes AS
SELECT t.id AS ticket, c.name AS cabana,
       date(t.closed_at) AS dia,
       t.issued_at AS entrada, t.closed_at AS salida,
       t.duration_min AS minutos,
       t.price AS base,
       round(COALESCE(t.total_charged, 0) - t.price, 0) AS servicios,
       COALESCE(t.total_charged, 0) AS total
FROM tickets t JOIN cabins c ON c.id = t.cabin_id
WHERE t.status = 'cerrado'
  AND strftime('%Y-%m', t.closed_at) = strftime('%Y-%m', 'now', 'localtime')
ORDER BY t.closed_at;

-- Todas las ocupaciones de cada cabana (estadias, pasadas y en curso)
CREATE VIEW IF NOT EXISTS v_ocupaciones_cabanas AS
SELECT c.name AS cabana, t.id AS ticket,
       t.issued_at AS entrada,
       COALESCE(t.closed_at, '') AS salida,
       CASE t.status WHEN 'activo' THEN 'EN CURSO'
                     WHEN 'cerrado' THEN 'FINALIZADA'
                     ELSE 'VENCIDA' END AS estado,
       CAST(round((julianday(COALESCE(t.closed_at, datetime('now', 'localtime')))
                   - julianday(t.issued_at)) * 24 * 60) AS INTEGER) AS minutos_ocupada,
       t.duration_min AS minutos_contratados,
       t.valid_until AS valido_hasta,
       t.entry_count AS entradas,
       t.price AS base,
       COALESCE(t.total_charged, 0) AS cobrado
FROM tickets t JOIN cabins c ON c.id = t.cabin_id
ORDER BY c.id, t.issued_at DESC;

-- Horarios mas ocupados de la semana en curso (lunes a hoy)
CREATE VIEW IF NOT EXISTS v_horarios_semana AS
SELECT strftime('%H', e.ts) || ':00' AS hora,
       COUNT(*) AS accesos,
       SUM(CASE WHEN e.kind = 'scan_ok' THEN 1 ELSE 0 END) AS entradas_qr,
       SUM(CASE WHEN e.kind = 'checkin' THEN 1 ELSE 0 END) AS ingresos_recepcion,
       COUNT(DISTINCT e.cabin_id) AS cabanas
FROM events e
WHERE e.kind IN ('scan_ok', 'checkin')
  AND date(e.ts) >= date('now', 'localtime', 'weekday 0', '-6 days')
  AND date(e.ts) <= date('now', 'localtime')
GROUP BY strftime('%H', e.ts)
ORDER BY accesos DESC;
"""


STAFF_SEED = [
    ("Limpieza", "Limpieza"),
    ("Mantenimiento", "Mantenimiento"),
    ("Administración", "Administración"),
]


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init():
    con = connect()
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
        for name, role in STAFF_SEED:
            while True:
                token = secrets.token_hex(8)
                short = token[:6].upper()
                busy = con.execute(
                    "SELECT 1 FROM tickets WHERE token=? OR token_short=?"
                    " UNION SELECT 1 FROM staff WHERE token=? OR token_short=?",
                    (token, short, token, short)).fetchone()
                if not busy:
                    break
            con.execute(
                "INSERT INTO staff(name, role, token, token_short) VALUES(?,?,?,?)",
                (name, role, token, short))
    con.commit()
    con.close()


def add_event(con, kind, cabin_id=None, device_id=None, detail=None):
    con.execute(
        "INSERT INTO events(kind, cabin_id, device_id, detail) VALUES(?,?,?,?)",
        (kind, cabin_id, device_id, detail),
    )
