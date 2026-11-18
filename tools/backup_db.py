#!/usr/bin/env python3
"""Respaldo consistente de la base de datos (se puede correr con el sistema andando).

Genera una copia en data/backups/ y conserva las ultimas 30.
Para automatizar: agregar a cron, por ejemplo cada hora:
    0 * * * * cd /home/jma/Documents/Proyect/motel-system && python3 tools/backup_db.py >> data/backups/backup.log 2>&1
"""

import datetime
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "server"))

import db  # noqa: E402


def main():
    out_dir = os.path.join(BASE, "data", "backups")
    os.makedirs(out_dir, exist_ok=True)
    name = "motel_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
    dest_path = os.path.join(out_dir, name)

    src = sqlite3.connect(db.DB_PATH)
    dst = sqlite3.connect(dest_path)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    backups = sorted(f for f in os.listdir(out_dir) if f.startswith("motel_"))
    for old in backups[:-30]:
        os.remove(os.path.join(out_dir, old))
    print(f"respaldo creado: {dest_path}")


if __name__ == "__main__":
    main()
