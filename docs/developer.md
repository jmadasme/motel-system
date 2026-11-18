# Motel System · developer

## Mapa del código

```text
motel-system/
├── server/              # backend Python estándar + SQLite
│   ├── app.py           # rutas HTTP y API
│   ├── db.py            # esquema y consultas
│   ├── doorctl.py       # HMAC, anti-replay y control de puerta
│   └── printer.py       # ticket ESC/POS y QR
├── firmware/nodemcu_cabin/  # NodeMCU ESP8266 + relay
├── maquetas/            # planos y material de la maqueta
├── docs/                # página, datasheet y developer
├── config.example.json  # configuración sanitizada
└── README.md
```

## Flujo de datos

1. `Recepción` — navegador
2. `Flask` — app.py
3. `SQLite` — estado
4. `NodeMCU` — cerradura
5. `Ticket` — ESC/POS

## Decisiones de diseño

- **QR con firma** (A): HMAC-SHA256 y ventana de validez para que un ticket no se reutilice.
- **Hardware simple** (B): Un ESP8266 con relé acciona la cerradura; el firmware está en PlatformIO.
- **Operación local** (C): Sin nube ni dependencias externas: la intranet vive en la red del recinto.

## Stack

Python, Flask, SQLite, ESP8266, PlatformIO, ESC/POS, HMAC-SHA256.

El servidor usa Flask y la biblioteca estándar; la base es SQLite y no requiere administración. El firmware del NodeMCU se compila con PlatformIO. La impresión térmica usa ESC/POS y el QR se firma en el servidor antes de imprimir.

## Cómo extenderlo

- Separá la lógica de dominio de la interfaz: el motor debe poder probarse sin navegador.
- Mantené los datos de demo fuera de la lógica y documentá su origen.
- Si agregás una integración externa, poné las credenciales en variables de entorno y un `.env.example` con `x`.
- Agregá una prueba de humo por cada flujo crítico antes de publicar.

## Puesta en marcha

```bash
# 1. Crear la configuración local
cp config.example.json config.json
# Editar panel_key, rutas de certificados (si usás HTTPS) y printer.mode

# 2. Arrancar el servidor
python3 server/app.py
# Abrir http://127.0.0.1:8080

# 3. Prueba de humo
python3 smoke_test.py

# 4. Firmware (PlatformIO)
cd firmware/nodemcu_cabin
pio run
pio run -t upload
```

## Seguridad

No se publican la base `data/motel.db`, los tickets, los logs, los certificados ni el `config.json` real. El firmware usa `config.example.h` con placeholders. La puerta se abre con HMAC-SHA256 y ventana anti-replay; el secreto debe ser el mismo en servidor y firmware.

## Límites conocidos

- **Red local**: Está pensado para una intranet. Exponerlo a internet requiere VPN, TLS y autenticación adicional.
- **Datos demo**: La base incluye cabañas y usuarios de ejemplo; no hay datos de huéspedes reales.
- **Hardware**: La cerradura y la impresora son específicas. El repo documenta el protocolo, no vende el hardware.
- **Configuración**: Las claves reales se reemplazan por `x` en los ejemplos; hay que definirlas al desplegar.

## Enlaces

- [README](../README.md)
- [Datasheet](datasheet.md)
- [Repositorio](https://github.com/jmadasme/motel-system)
