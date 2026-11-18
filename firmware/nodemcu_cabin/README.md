# Firmware NodeMCU ESP8266

Cada cabaña (y la barrera) lleva una placa **NodeMCU ESP8266** con el módulo
relé. El firmware:

- Atiende órdenes de apertura **firmadas con HMAC-SHA256** enviadas por el
  servidor central por WiFi (HTTP). Sin firma válida → 401.
- Detecta y rechaza comandos repetidos (anti-replay).
- Botón físico interior: abre 5 segundos **sin pedir autorización** y avisa
  al servidor (evento `exit_button`).
- Heartbeat cada 30 s → el panel muestra si la placa está en línea.

## Conectar la placa

| NodeMCU | Módulo relé | Nota |
|---|---|---|
| D1 (GPIO5) | IN | señal de la chapa |
| GND | GND | |
| 3V3/VIN | VCC | según módulo (5V suele necesitar VIN) |
| D2 (GPIO4) | — | botón interior a GND |
| D4 (GPIO2) | — | LED onboard |

La **chapa eléctrica** se alimenta con su propia fuente (12 V típico). El relé
solo corta/pega el negativo de la chapa. Usar cable de **datos** para
programar (no sirve el de solo carga).

## Flashear

1. `cp include/config.example.h include/config.h` y editar:
   - WiFi del motel,
   - `DEVICE_ID` y `DEVICE_KEY` **idénticos** a la fila que se cree en la
     base de datos del servidor (el seed crea `cab01`, `cab02`, … `gate-01`).
2. `pio run -t upload && pio device monitor`

Si no hay PlatformIO: `pip install platformio`.

## Probar sin CNC

```
curl "http://<ip-placa>/status"
# apertura firmada (el servidor lo hace solo; esto es para pruebas):
#   se necesitan ts, r y firma HMAC con DEVICE_KEY. Ver tools/sim_device.py.
```
