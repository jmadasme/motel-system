# Flujo funcional del sistema

Documento de referencia del comportamiento acordado con el cliente.
Toda la lógica aquí descrita está implementada en `server/app.py`.

## Actores

| Actor | Qué usa | Clave |
|---|---|---|
| Recepcionista | `/recepcion`, `/kitchen` | clave de panel |
| Cliente (llegada) | citófono + ticket impreso | — |
| Cliente (puerta) | teléfono-escáner en la puerta | `k` de la cabaña |
| Cliente (interior) | teléfono con catálogo `/cabana` | `k` de la cabaña |
| Cocina | `/kitchen` | clave de panel |
| Administración | `/dashboard` | clave de panel |
| Placas ESP8266 | red WiFi | secreto por dispositivo (HMAC) |

## Secuencia (caso feliz)

```
Chofer        Recepcionista        Servidor           Tel.Puerta     NodeMCU
  │  pide cabaña  │                  │                   │             │
  │──────────────▶│                  │                   │             │
  │               │ POST /api/checkin│                   │             │
  │               │─────────────────▶│                   │             │
  │               │                  │ crea ticket QR    │             │
  │               │                  │ imprime ticket    │             │
  │               │                  │ abre barrera ─────┼────────────▶│ (relé 1.5 s)
  │  ◀── ticket con QR ──────────────│                   │             │
  │                                   │                  │             │
  │  llega a la puerta y presenta el QR ────────────────▶│             │
  │                                   │  POST /api/scan  │             │
  │                                   │◀─────────────────│             │
  │                                   │ valida:          │             │
  │                                   │  - existe        │             │
  │                                   │  - activo        │             │
  │                                   │  - no vencido    │             │
  │                                   │  - misma cabaña  │             │
  │                                   │ orden firmada ───┼────────────▶│ (relé 1.0 s)
  │                                   │ 200 OK ─────────▶│  ✅         │
  │  entra                            │                  │             │
```

## Acciones del cliente

- **Entrar**: presentar el QR al teléfono-escáner. Cada entrada queda contada
  (`entry_count`) y puede repetirse mientras la estadía esté activa
  (`qr_policy = "multi"` en `config.json`; con `"one_time"` el QR solo sirve
  una vez).
- **Pedir alimentos**: en la app del catálogo, armar el carrito y enviar. La
  cocina lo ve al instante y queda sumado a la cuenta.
- **Salir con urgencia**: botón físico interior (sin autorización, 5 s) o el
  botón equivalent de la app (mismo efecto). Queda registrado como evento
  `salida` / `exit_button`.

## Reglas de validación del QR (código `MTL1-…`)

1. Código desconocido → **ACCESO DENEGADO** ("Código no reconocido").
2. Ticket de otra cabaña → **DENEGADO** ("Este ticket es de Cabaña X").
3. Ticket cerrado (checkout hecho) → **DENEGADO**.
4. Fuera del horario pagado → **DENEGADO** ("Ticket vencido") y pasa a estado
   `vencido`.
5. Con `one_time`: segundo uso → **DENEGADO** ("Ticket ya utilizado").
6. Todo correcto → **PERMITIDO**: se registra la entrada y se abre la chapa.

Además, el endpoint exige la clave `k` de la cabaña: un teléfono cualquiera
no puede pedir aperturas.

## Estados

- Cabaña: `libre` → `ocupada` → `libre` (checkout).
- Ticket: `activo` → `cerrado` | `vencido`.
- Pedido: `nuevo` → `preparando` → `listo` → `entregado` (o `cancelado`).

## Dinero (fase actual)

- Precio base según tiempo elegido (3/6/12 h) — se define por cabaña en la
  tabla `cabins`.
- Servicios = suma de pedidos no cancelados del ticket.
- Total de la estadía = base + servicios (visible en panel y en el checkout).
- **El cobro aún no está integrado**: recepción cobra y marca la salida; no
  hay pasarela de pago ni cierre de caja por turno (ver README → Pendiente).

## Bitácora de eventos

Cada evento queda en la tabla `events` con hora local:

`checkin`, `checkout`, `scan_ok`, `scan_denegado`, `puerta` (apertura manual
o por QR), `salida` (botón app), `barrera`, `pedido`, `pedido_estado`,
`reimpresion`, `dispositivo:unlock_remote`, `dispositivo:exit_button`.

## Seguridad del canal servidor → placa

- El servidor firma cada orden: `HMAC-SHA256(secreto_dispositivo,
  "<timestamp>:<ms>:<nonce>")` en headers `X-Timestamp` / `X-Signature`.
- La placa rechaza firma inválida (401), timestamp sospechoso y comandos
  repetidos (anti-replay, últimos 16 comandos).
- El sentido inverso (heartbeat/eventos de la placa) también va firmado.
- Los secretos viven en la tabla `devices` y en `config.h` de cada placa.

## Responsabilidad de cada componente

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Servidor central | `server/app.py` | validar QR, abrir puertas, tickets, pedidos, panel |
| Datos | `server/db.py` | SQLite (cabins, devices, tickets, events, products, orders) |
| Puertas | `server/doorctl.py` | firma HMAC y envío HTTP a las placas |
| Tickets | `server/printer.py` | ESC/POS con QR nativo; red / CUPS / archivo |
| Placa | `firmware/.../main.cpp` | relé, botón de salida, anti-replay, heartbeat |
| Simulador | `tools/sim_device.py` | probar el protocolo sin hardware |
