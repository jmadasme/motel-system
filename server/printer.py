"""Impresion del ticket QR en impresora termica.

Sin dependencias externas. El QR se genera de forma NATIVA por la impresora
(comando ESC/POS GS ( k), o sea no se manda ninguna imagen.

Modos (config.json -> printer.mode):
  - "file"    : guarda el ticket binario + vista previa en data/tickets/ (pruebas)
  - "network" : manda los bytes ESC/POS a la impresora de red (puerto 9100 raw)
  - "command" : ejecuta un comando (ej: CUPS -> "lp -o raw -d POS-80") con el
                ticket en stdin
"""

import os
import shlex
import socket
import subprocess
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GS = b"\x1d"


# ---------------------------------------------------------------- utilidades

def fmt_clp(value):
    n = int(round(float(value)))
    return "$ " + f"{n:,}".replace(",", ".")


def dur_label(minutes):
    minutes = int(minutes)
    if minutes % 60 == 0:
        h = minutes // 60
        return f"{h} hora" + ("s" if h != 1 else "")
    return f"{minutes} min"


def _a(text):
    """Texto plano a bytes para ESC/POS, sin acentos (compatibilidad)."""
    norm = unicodedata.normalize("NFKD", str(text))
    return norm.encode("ascii", "ignore")


# -------------------------------------------------------------------- QR ESC/POS

def qr_escpos(payload, module=6, ec=49):
    """Genera el bloque ESC/POS que hace que la impresora dibuje el QR.

    module: tamano de modulo (1-16). ec: 48=L, 49=M, 50=Q, 51=H.
    """
    data = payload.encode("ascii", "replace")
    length = len(data) + 3
    pl, ph = length & 0xFF, (length >> 8) & 0xFF
    out = b""
    out += GS + b"(k" + bytes([4, 0, 49, 65, 50, 0])        # modelo 2
    out += GS + b"(k" + bytes([3, 0, 49, 67, module])        # tamano modulo
    out += GS + b"(k" + bytes([3, 0, 49, 69, ec])            # nivel correccion
    out += GS + b"(k" + bytes([pl, ph, 49, 80, 48]) + data   # guardar datos
    out += GS + b"(k" + bytes([3, 0, 49, 81, 48])            # imprimir
    return out


# ---------------------------------------------------------------------- ticket

def ticket_text(cfg, t, cabin_name, payload):
    """Vista previa en texto (UTF-8, con acentos)."""
    lines = [
        cfg["motel"]["name"].upper(),
        "-" * 32,
        f"Cabana       : {cabin_name}",
        f"Ticket       : #{t['id']}",
        f"Tiempo       : {dur_label(t['duration_min'])}",
        f"Valor        : {fmt_clp(t['price'])}",
        f"Valido hasta : {str(t['valid_until'])[11:16]}",
        "-" * 32,
        f"Codigo QR    : {payload}",
        f"Codigo manual: {t['token_short']}",
        "-" * 32,
        "Presente este codigo en la puerta",
        "de su cabana. Gracias.",
        "",
    ]
    return "\n".join(lines)


def escpos_ticket(cfg, t, cabin_name, payload):
    out = bytearray()
    out += b"\x1b@"                                  # init
    out += b"\x1b\x61\x01"                           # centrado
    out += b"\x1b\x45\x01" + _a(cfg["motel"]["name"].upper()) + b"\n" + b"\x1b\x45\x00"
    out += _a("-" * 32) + b"\n"
    out += b"\x1b\x61\x00"                           # izquierda
    rows = [
        ("Cabana", cabin_name),
        ("Ticket", f"#{t['id']}"),
        ("Tiempo", dur_label(t["duration_min"])),
        ("Valor", fmt_clp(t["price"])),
        ("Valido hasta", str(t["valid_until"])[11:16]),
    ]
    for key, val in rows:
        out += _a(f"{key:<13}: {val}\n")
    out += _a("-" * 32) + b"\n"
    out += b"\x1b\x61\x01"                           # centrado para el QR
    out += qr_escpos(payload)
    out += _a(f"Manual: {t['token_short']}\n")
    out += _a("Presente este codigo en la puerta\n")
    out += _a("de su cabana. Gracias.\n\n\n\n")
    out += b"\x1dV\x42\x00"                          # avance + corte
    return bytes(out)


# ----------------------------------------------------------------- envio

def send(cfg, ticket_bytes, text, base_name):
    """Envia el ticket segun el modo configurado."""
    mode = cfg["printer"].get("mode", "file")
    try:
        if mode == "network":
            host = cfg["printer"]["host"]
            port = int(cfg["printer"].get("port", 9100))
            with socket.create_connection((host, port), timeout=5) as sock:
                sock.sendall(ticket_bytes)
            return {"ok": True, "mode": mode, "detail": f"enviado a {host}:{port}"}

        if mode == "command":
            cmd = shlex.split(cfg["printer"]["command"])
            proc = subprocess.run(cmd, input=ticket_bytes, timeout=15,
                                  capture_output=True)
            ok = proc.returncode == 0
            return {"ok": ok, "mode": mode,
                    "detail": (proc.stdout + proc.stderr).decode(errors="replace").strip()
                              or f"exit {proc.returncode}"}

        # modo archivo (default de pruebas)
        out_dir = os.path.join(BASE, cfg["printer"].get("dir", "data/tickets"))
        os.makedirs(out_dir, exist_ok=True)
        bin_path = os.path.join(out_dir, base_name + ".bin")
        txt_path = os.path.join(out_dir, base_name + ".txt")
        with open(bin_path, "wb") as fh:
            fh.write(ticket_bytes)
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return {"ok": True, "mode": "file", "detail": bin_path, "preview": txt_path}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "mode": mode, "detail": str(exc)}
