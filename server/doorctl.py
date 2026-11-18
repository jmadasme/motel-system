"""Control de puertas/barreras.

El servidor central envia un comando por la red WiFi (HTTP) a la placa
NodeMCU ESP8266 de cada cabana. El comando va firmado con HMAC-SHA256 y un
nonce, para que nadie en la red pueda abrir puertas sin autorizacion.

Dispositivos con ip = "virtual" no tienen hardware: el servidor los simula
(util para demo y pruebas).
"""

import hashlib
import hmac
import secrets as _secrets
import time
import urllib.request

REPLAY_WINDOW_S = 60


def sign(secret, canonical):
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def verify(secret, canonical, signature, ts=None, window=REPLAY_WINDOW_S):
    """Verifica firma HMAC y (si ts viene) que no sea vieja."""
    if ts is not None:
        try:
            ts_i = int(ts)
        except (TypeError, ValueError):
            return False, "timestamp invalido"
        if abs(time.time() - ts_i) > window:
            return False, "timestamp fuera de ventana"
    expected = sign(secret, canonical)
    if not signature or not hmac.compare_digest(expected, signature):
        return False, "firma invalida"
    return True, "ok"


def unlock(dev, ms=None):
    """Envia orden de apertura a un dispositivo. dev: sqlite3.Row o dict.

    Devuelve {"ok": bool, "simulated": bool, "detail": str}
    """
    ms = int(ms or dev["relay_ms"] or 1000)
    ms = max(200, min(ms, 15000))
    dev_id = dev["id"]

    if not dev["ip"] or dev["ip"] == "virtual":
        return {"ok": True, "simulated": True,
                "detail": f"SIMULADO: rele {ms} ms ({dev_id}, sin hardware)"}

    ts = str(int(time.time()))
    r = _secrets.token_hex(4)
    canonical = f"{ts}:{ms}:{r}"
    sig = sign(dev["secret"], canonical)
    url = f"http://{dev['ip']}:{dev['port']}/unlock?ms={ms}&r={r}"
    req = urllib.request.Request(
        url,
        headers={"X-Timestamp": ts, "X-Signature": sig, "User-Agent": "motel-server/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            body = resp.read(200).decode(errors="replace").strip()
        return {"ok": True, "simulated": False, "detail": f"{url} -> {body}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "simulated": False, "detail": f"{url} -> ERROR: {exc}"}
