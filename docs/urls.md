# Catálogo de URLs — propósito y uso

Base de todas las direcciones: `http://IP-DEL-PC-CENTRAL:8080`
(en la práctica: `http://192.168.1.100:8080`, o `http://localhost:8080` si se
usa el mismo computador; con HTTPS si se generó el certificado).

---

## 1. Páginas web (lo que se abre en el navegador)

| URL | Para qué sirve | Quién la usa |
|---|---|---|
| `/` | Menú de acceso con todas las pantallas | administración |
| `/recepcion` | **Mostrador**: registrar ingreso (imprime ticket QR y abre barrera), reimprimir, abrir puertas a mano, cobrar salida | recepcionista |
| `/scan?cab=N` | **Escáner de puerta**: lee el QR y pide la apertura al servidor | teléfono fijo de la puerta de la cabaña N |
| `/cabana?cab=N` | **Catálogo de la cabaña**: pedir alimentos/bebidas a cocina y abrir la puerta para salir (5 s) | teléfono fijo interior de la cabaña N |
| `/kitchen` | **Cocina**: cola de pedidos por estado (recibido → preparando → listo → entregado) | cocinero |
| `/dashboard` | **Panel**: ocupación en vivo, tiempos, cargos, estado de cada placa y bitácora de eventos | administración / supervisión |
| `/ingresos` | **Ingresos**: cobrado hoy y del mes, gráfico de 14 días, estadías en curso e historial con descarga Excel | administración / dueño |
| `/maquetas/index.html` | Galería de **maquetas** (páginas de ejemplo con datos ficticios, sin base real) | mostrar/vender el sistema |
| `/style.css` | Hoja de estilos común de todas las páginas | interno (navegador) |
| `/vendor/qrcode.js` | Librería que dibuja el QR en el navegador (recepción) | interno (navegador) |
| `/vendor/jsQR.js` | Librería que **lee** el QR con la cámara (escáner) | interno (navegador) |

**Provisionar teléfonos:** las URLs exactas de cada cabaña (con su número y
clave) se ven en `/dashboard` → sección "Provisionar teléfonos por cabaña".
Formato: `/scan?cab=3&k=CLAVE` y `/cabana?cab=3&k=CLAVE`.

---

## 2. Claves en las URLs (`?k=…`) y clave de panel

Depende del modo configurado en `config.json` → `"require_keys"`:

| Modo | Cómo se comporta |
|---|---|
| `false` (demo) | Todo entra directo; `?cab=N` basta, la `k` es opcional |
| `true` (producción) | Las pantallas de personal piden la clave de panel (una vez por navegador); `/scan` y `/cabana` exigen la `k` de esa cabaña en la URL |

La `k` de cada cabaña está en la base (tabla `cabins.scanner_key`) y se cambia
con la herramienta de siembra/administración. La clave de panel
(`panel_key`) protege TODAS las pantallas de personal y las APIs marcadas
"clave panel" más abajo.

---

## 3. API del servidor (JSON; para integraciones o diagnóstico)

### Consultas

| URL | Método | Qué devuelve | Auth |
|---|---|---|---|
| `/api/config` | GET | modo de claves y nombre del motel (lo usan las páginas al abrir) | pública |
| `/api/state` | GET | TODO el estado: cabañas, tickets activos, dispositivos, eventos, totales | clave panel |
| `/api/products` | GET | catálogo de productos activos con precios | pública |
| `/api/cabin_state?cab=N&k=…` | GET | estado/ticket/pedidos de una cabaña (lo usa su catálogo) | clave cabaña |
| `/api/orders` | GET | cola de cocina (activos + entregados recientes) | clave panel |
| `/api/revenue` | GET | ingresos: hoy, mes, en curso, historial y últimos 14 días | clave panel |
| `/api/revenue/export.xlsx` | GET | descarga del Excel de ingresos (hojas Resumen, EnCurso, Cobros). Acepta `?k=CLAVE` para descarga directa | clave panel |

### Acciones

| URL | Método | Qué hace | Auth |
|---|---|---|---|
| `/api/checkin` | POST | registra ingreso: crea ticket QR, imprime, abre barrera. Cuerpo: `{"cabin_id":5,"duration_min":180,"plate":"ABCD12"}` | clave panel |
| `/api/checkout` | POST | cobra y libera la cabaña, abre barrera. Cuerpo: `{"cabin_id":5}` | clave panel |
| `/api/scan` | POST | valida un QR en la puerta y abre 1 s. Cuerpo: `{"cab":5,"k":"…","code":"MTL1-…"}` | clave cabaña |
| `/api/panel/open` | POST | apertura manual de una cabaña (queda en bitácora). Cuerpo: `{"cabin_id":5}` | clave panel |
| `/api/gate/open` | POST | abre la barrera (pulso 1,5 s) | clave panel |
| `/api/reprint` | POST | reimprime el último ticket de una cabaña. Cuerpo: `{"cabin_id":5}` | clave panel |
| `/api/orders` | POST | crea pedido desde la cabaña. Cuerpo: `{"cab":5,"k":"…","items":[{"product_id":1,"qty":2}]}` | clave cabaña |
| `/api/orders/status` | POST | avanza/cancela pedido. Cuerpo: `{"order_id":88,"status":"preparando"}` | clave panel |
| `/api/exit_request` | POST | abre 5 s para salir (botón de la app interior). Cuerpo: `{"cab":5,"k":"…"}` | clave cabaña |

### Dispositivos (las placas)

| URL | Método | Qué hace | Auth |
|---|---|---|---|
| `/api/devices/heartbeat` | POST | la placa avisa "estoy vivo" (el panel marca en línea/desconectada) | firma HMAC de la placa |
| `/api/devices/event` | POST | la placa informa eventos (botón de salida, apertura remota) | firma HMAC de la placa |

Ejemplo de uso manual (diagnóstico):

```bash
# estado completo (con claves desactivadas)
curl http://localhost:8080/api/state

# registrar un ingreso de prueba
curl -X POST http://localhost:8080/api/checkin \
     -H 'Content-Type: application/json' \
     -d '{"cabin_id":5,"duration_min":180}'
```

---

## 4. URLs de las placas NodeMCU (firmware)

Cada placa expone su propio mini servidor en su IP (ej. `192.168.1.63`).
La red llama a estas URLs; el personal normalmente no las usa.

| URL | Para qué sirve | Quién la llama |
|---|---|---|
| `http://IP-PLACA/unlock?ms=1000&r=nonce` | orden de apertura: activa el relé `ms` milisegundos (requiere los headers firmados `X-Timestamp` y `X-Signature`; sin firma responde 401) | el servidor central, por WiFi |
| `http://IP-PLACA/status` | diagnóstico: ID, firmware, IP, señal WiFi, estado del relé y último motivo | cualquiera en la red (solo lectura) |

Ejemplo:

```bash
curl http://192.168.1.63/status
# {"ok":true,"device_id":"cab03","kind":"cabin","fw":"1.0.0","ip":"192.168.1.63",
#  "rssi":-54,"uptime":4821,"relay":false,"last":"remoto QR"}
```

El pulso del botón interior (5 s sin autorización) **no** usa URL: es físico y
queda registrado como evento vía `/api/devices/event`.

---

## 5. Simulador (solo desarrollo, sin hardware)

| URL | Para qué sirve |
|---|---|
| `http://127.0.0.1:9081/status` | ver cómo respondería una placa simulada |
| `http://127.0.0.1:9081/sim/exit` | simular el botón de salida (abre 5 s y avisa al servidor) |
| `http://127.0.0.1:9081/sim/heartbeat` | forzar un latido de la placa simulada |
| `http://127.0.0.1:9081/unlock?ms=1000&r=x` | probar que rechaza órdenes sin firma (401) |

Se levantan con `python3 tools/sim_device.py --id cab01 --port 9081`.

---

## 6. Resumen de quién abre qué

| Puesto | URL que deja abierta |
|---|---|
| Recepción (PC) | `/recepcion` |
| Cocina (pantalla) | `/kitchen` |
| Administración (PC) | `/dashboard` e `/ingresos` |
| Cada puerta de cabaña | `/scan?cab=N` (teléfono en kiosco) |
| Cada interior | `/cabana?cab=N` (teléfono en kiosco) |
