#!/usr/bin/env python3
"""Prueba end-to-end de un link de pago de Mercado Pago.

Crea una preferencia (link de pago) atada a una referencia propia y despues
consulta la API cada pocos segundos hasta que el pago aparece como aprobado.
No necesita IP publica ni webhook: funciona por polling desde esta maquina.

El Access Token se lee de la variable MP_ACCESS_TOKEN o del archivo
data/mp_token.txt. Nunca se imprime.

Como conseguir el token (cuenta vendedor de Mercado Pago):
  1. Entrar a https://www.mercadopago.cl/developers/panel/app
  2. Crear una aplicacion (o usar una existente).
  3. Copiar el Access Token de produccion (empieza con APP_USR-).
  4. Guardarlo en data/mp_token.txt (data/ ya esta en .gitignore).

Uso:
    python3 tools/mp_link_test.py --amount 500
    python3 tools/mp_link_test.py --amount 500 --ref prueba-esposa
    python3 tools/mp_link_test.py --watch-only --ref prueba-esposa
    python3 tools/mp_link_test.py --create-only --amount 500

OJO: con credenciales de produccion el pago es con dinero real.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.mercadopago.com"
TOKEN_FILE = os.path.join(BASE, "data", "mp_token.txt")


def load_token():
    token = os.environ.get("MP_ACCESS_TOKEN", "").strip()
    if token:
        return token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            token = fh.read().strip()
        if token:
            return token
    sys.exit(
        "Falta el Access Token de Mercado Pago.\n"
        "Ponelo en la variable MP_ACCESS_TOKEN o en data/mp_token.txt\n"
        "Lo sacas de https://www.mercadopago.cl/developers/panel/app"
    )


def api(method, path, token, payload=None):
    data = None
    headers = {"Authorization": "Bearer " + token}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        sys.exit(f"Error HTTP {exc.code} de Mercado Pago:\n{body}")
    except urllib.error.URLError as exc:
        sys.exit(f"No se pudo conectar con Mercado Pago: {exc.reason}")


def create_link(token, amount, currency, reference):
    preference = {
        "items": [
            {
                "title": "Prueba de pago",
                "description": "Pago de prueba del sistema",
                "quantity": 1,
                "currency_id": currency,
                "unit_price": amount,
            }
        ],
        "external_reference": reference,
    }
    result = api("POST", "/checkout/preferences", token, preference)
    if token.startswith("TEST-") and result.get("sandbox_init_point"):
        link = result["sandbox_init_point"]
    else:
        link = result.get("init_point") or result.get("sandbox_init_point")
    if not link:
        sys.exit("Mercado Pago no devolvio un link de pago: " + json.dumps(result))
    return link, result.get("id", "")


def find_payments(token, reference):
    query = urllib.parse.urlencode(
        {
            "external_reference": reference,
            "sort": "date_created",
            "criteria": "desc",
            "limit": 20,
        }
    )
    result = api("GET", "/v1/payments/search?" + query, token)
    return result.get("results") or []


def describe(payment):
    return (
        f"id={payment.get('id')} estado={payment.get('status')} "
        f"detalle={payment.get('status_detail')} "
        f"monto={payment.get('transaction_amount')} {payment.get('currency_id', '')}"
    )


def watch(token, reference, interval, timeout):
    print(f"Vigilando pagos con referencia: {reference}")
    print("(Ctrl+C para cortar)\n")
    seen = {}
    started = time.time()
    while time.time() - started < timeout:
        payments = find_payments(token, reference)
        for payment in payments:
            pid = str(payment.get("id"))
            status = payment.get("status")
            if seen.get(pid) == status:
                continue
            seen[pid] = status
            print(f"[{dt.datetime.now():%H:%M:%S}] {describe(payment)}")
            if status == "approved":
                print("\nPAGO APROBADO. El comercio ya se entero.")
                print(f"Referencia: {reference}")
                print(f"Pago: {payment.get('id')}")
                return 0
        time.sleep(interval)
    print(f"\nNo se detecto un pago aprobado en {timeout} segundos.")
    return 1


def main():
    parser = argparse.ArgumentParser(description="Prueba de link de pago de Mercado Pago")
    parser.add_argument("--amount", type=float, default=500, help="monto a cobrar (default 500)")
    parser.add_argument("--currency", default="CLP", help="moneda (default CLP)")
    parser.add_argument("--ref", default="", help="referencia externa del pedido")
    parser.add_argument("--interval", type=int, default=5, help="segundos entre consultas")
    parser.add_argument("--timeout", type=int, default=900, help="segundos maximos de espera")
    parser.add_argument("--create-only", action="store_true", help="solo crear el link y salir")
    parser.add_argument("--watch-only", action="store_true", help="solo vigilar una referencia existente")
    args = parser.parse_args()

    if args.amount <= 0:
        sys.exit("El monto debe ser mayor que cero.")
    if args.interval < 2:
        sys.exit("El intervalo minimo es de 2 segundos, para no saturar la API.")

    token = load_token()
    reference = args.ref.strip()
    if not reference:
        reference = "prueba-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    link = None
    if not args.watch_only:
        link, pref_id = create_link(token, args.amount, args.currency, reference)
        print("Link de pago creado.")
        print(f"  Referencia: {reference}")
        print(f"  Preferencia: {pref_id}")
        print(f"  Monto: {args.amount:g} {args.currency}")
        print(f"\nLINK PARA PAGAR:\n{link}\n")
        print("Mandalo a tu senora. Cuando pague, este programa lo detecta.\n")
        if args.create_only:
            return 0

    if args.watch_only:
        print(f"Link no creado en esta corrida (referencia: {reference}).\n")

    return watch(token, reference, args.interval, args.timeout)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
