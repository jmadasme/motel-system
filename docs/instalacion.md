# Guía de instalación y puesta en marcha (checklist real)

Orden de trabajo para dejar el sistema funcionando en un motel. Está pensada
para imprimirse y marcar casillas. Ejemplo base: **8 cabañas** (escala igual
para más: todo es proporcional).

---

## 0. Compras y preparación

**Hardware (por 8 cabañas)**

| # | Componente | Cantidad | Notas |
|---|---|---|---|
| 1 | Mini-PC Linux (Intel N100 o i3, 8 GB RAM, SSD 128 GB+) | 1 | el "servidor central" |
| 2 | UPS 600–1000 VA | 1 | PC + router + APs |
| 3 | Teléfono Android (gama media, 5"+, 2 GB RAM+) | 16 | 8 puerta + 8 interior |
| 4 | Cargador + cable fijo por teléfono + soporte | 16 | energía permanente |
| 5 | NodeMCU ESP8266 + módulo relé 5V | 9 | 8 cabañas + 1 barrera |
| 6 | Chapa eléctrica 12V + fuente 12V | 8 | ver nota "fail-safe" abajo |
| 7 | Pulsador interior (salida de emergencia) | 8 | siempre operativo, sin autorización |
| 8 | Impresora térmica ESC/POS (red 9100 o USB) con autocorte | 1 | + 20 rollos de repuesto |
| 9 | Router + 1–2 APs (2.4 GHz para ESP8266) | 2–3 | SSID exclusivo del sistema |
| 10 | Lamparita LED por puerta | 8 | para leer el QR de noche |
| 11 | Cable de DATOS micro-USB (para flashear) | 2 | ¡no sirve el de solo carga! |

**Software**

- [ ] PC central con Ubuntu (o similar) actualizado.
- [ ] Proyecto copiado: `~/motel-system` (este repo).
- [ ] `python3 --version` ≥ 3.8 (viene casi siempre).
- [ ] En el PC de trabajo: [PlatformIO](https://platformio.org) para flashear placas.

**Nota chapas:** idealmente *fail-safe* (sin energía = abierta desde adentro)
o bien que el encierro sea seguro: el botón interior debe abrir SIEMPRE,
incluso sin WiFi ni energía del sistema (batería de respaldo para la chapa
o cerradura mecánica interior).

---

## 1. Red interna

- [ ] Crear SSID exclusivo del sistema (ej. `MOTEL-SISTEMA`), WPA2, **2.4 GHz activo** (las NodeMCU solo usan 2.4).
- [ ] Cambiar usuario/clave por defecto del router y APs.
- [ ] Reservar IP fija por MAC (o IP estática) para:
  - PC central (ej. `192.168.1.100`),
  - impresora (ej. `192.168.1.50`),
  - cada NodeMCU (ej. `192.168.1.61`…`192.168.1.68`, barrera `192.168.1.60`).
- [ ] Anotar todo en la tabla del final de este documento.
- [ ] Verificar cobertura WiFi **en cada puerta** (señal > −70 dBm; si no, AP extra).
- [ ] Conectar UPS a PC + router + APs.

---

## 2. Servidor central (PC Linux)

- [ ] `cd ~/motel-system && ./start.sh` → comprobar que abre `http://IP:8080/dashboard`.
- [ ] Editar `config.json`:
  - [ ] `require_keys`: poner `true` (producción),
  - [ ] `panel_key`: clave nueva y larga (anotarla),
  - [ ] `printer`: modo `network` con IP de la impresora, o `command` con CUPS.
- [ ] HTTPS para las cámaras: `./make_cert.sh` (genera el certificado y activa `"https": true` solo).
- [ ] Sembrar la base real: `python3 tools/seed_demo.py --reset` y **editar cabañas/precios** (o pedir una herramienta de administración).
- [ ] Respaldo automático:
  - [ ] `crontab -e` y agregar:
    `0 * * * * cd /home/jma/Documents/Proyect/motel-system && python3 tools/backup_db.py >> data/backups/backup.log 2>&1`
  - [ ] copia semanal a USB o segundo PC.
- [ ] Arranque automático al encender el PC. Crear `deploy/motel.service` y:
  ```
  sudo cp deploy/motel.service /etc/systemd/system/
  sudo systemctl enable --now motel
  ```
  (archivo de ejemplo en `deploy/motel.service`, ajustar usuario/ruta si cambia).
- [ ] Probar: apagar y encender el PC → el sistema debe volver solo.

---

## 3. Impresora térmica

- [ ] Conectar (red o USB) e imprimir página de prueba del fabricante.
- [ ] Modo red: `nc -v 192.168.1.50 9100` no debe dar "connection refused".
- [ ] Modo USB/CUPS: `lp -o raw -d NOMBRE_COLA /dev/null` sin errores.
- [ ] Desde Recepción: registrar un ingreso de prueba → **sale el ticket con QR**.
- [ ] Ajustar en el ticket lo que haga falta (acentos, ancho 58/80 mm).

---

## 4. NodeMCU (por cada puerta + barrera)

Por cada placa:

- [ ] `cp include/config.example.h include/config.h` y editar:
  - [ ] `WIFI_SSID` / `WIFI_PASS` de la red del sistema,
  - [ ] `DEVICE_ID` (ej. `cab03`) y `DEVICE_KEY` (el secreto que figure en la tabla `devices` del servidor),
  - [ ] `SERVER_HOST` = IP del PC central.
- [ ] `pio run -t upload` con **cable de datos**.
- [ ] Cablear: D1→IN relé, D2→pulsador interior (a GND), GND común, fuente 12V para la chapa.
- [ ] Probar: `curl http://192.168.1.63/status` → responde JSON con IP y relé.
- [ ] En la base (o con el administrador): `devices.ip` = IP real de la placa, `secret` = `DEVICE_KEY`.
- [ ] En el panel, la placa debe pasar a **"en línea"** en <1 minuto (heartbeat).
- [ ] Verificar botón interior: abre 5 s y queda el evento `exit_button` en la bitácora.

---

## 5. Teléfonos (kiosco)

Por cada teléfono:

- [ ] WiFi del sistema conectado, batería > 20 % siempre (energía fija), optimización de batería desactivada.
- [ ] Abrir `https://IP:8080` → aceptar el aviso de certificado (una sola vez por teléfono).
- [ ] **Puerta**: abrir `https://IP:8080/scan?cab=N`
  - [ ] botón "Encender cámara" → permitir cámara,
  - [ ] dejar en pantalla completa, brillo alto, pantalla siempre encendida,
  - [ ] guardar como acceso directo en la pantalla de inicio (o kiosco).
- [ ] **Interior**: abrir `https://IP:8080/cabana?cab=N` → pantalla de inicio igual.
- [ ] Etiquetar físicamente cada teléfono: "CABAÑA 3 – PUERTA" / "CABAÑA 3 – INTERIOR".
- [ ] Montaje: puerta a la altura de la ventanilla del auto; interior junto a la mesa.
- [ ] Lamparita LED de la puerta probada de noche.

---

## 6. Pruebas por cabaña (una por una)

Marcar por cada cabaña N:

| Prueba | ✔ |
|---|---|
| Registrar ingreso en Recepción → sale ticket con QR | |
| El QR abre **esa** puerta (1 segundo) | |
| El QR de otra cabaña es **rechazado** en esa puerta | |
| Código manual de 6 letras del ticket también abre | |
| Botón interior abre 5 s (de día y de noche) | |
| Pedido desde el teléfono interior llega a Cocina y suma a la cuenta | |
| Cobrar la salida libera la cabaña y abre la barrera | |
| La placa aparece "en línea" en el Panel | |
| El escáner lee el QR de noche | |

---

## 7. Capacitación y operación diaria

- [ ] Recepción: registrar ingreso, reimprimir ticket, abrir a mano, cobrar salida.
- [ ] Cocina: cola de pedidos y cambio de estados.
- [ ] Administración: panel, ingresos, Excel, bitácora (para auditoría).
- [ ] Regla de oro: **todo ingreso pasa por el sistema**; ninguna apertura manual sin registro.

---

## 8. Mantenimiento

- [ ] Semanal: mirar bitácora de aperturas manuales (señal de irregularidad).
- [ ] Mensual: verificar respaldos (`data/backups/`) y probar restaurar uno.
- [ ] Mensual: revisar pilas/energía de teléfonos y limpiar lentes de cámara.
- [ ] Al cambiar un teléfono o placa: actualizar su fila en `devices` / etiqueta.
- [ ] Guardar las claves (`panel_key`, secretos de placas) en lugar seguro.

---

## Tabla para completar en terreno

| Cabaña | Dispositivo (DEVICE_ID) | Secreto (DEVICE_KEY) | IP placa | Tel puerta | Tel interior |
|---|---|---|---|---|---|
| 1 | cab01 | | 192.168.1.61 | | |
| 2 | cab02 | | 192.168.1.62 | | |
| 3 | cab03 | | 192.168.1.63 | | |
| 4 | cab04 | | 192.168.1.64 | | |
| 5 | cab05 | | 192.168.1.65 | | |
| 6 | cab06 | | 192.168.1.66 | | |
| 7 | cab07 | | 192.168.1.67 | | |
| 8 | cab08 | | 192.168.1.68 | | |
| Barrera | gate-01 | | 192.168.1.60 | — | — |

Otros datos: PC central `______` · Impresora `______` · Clave panel `______`

---

## Problemas típicos

| Síntoma | Causa probable | Solución |
|---|---|---|
| La placa no aparece nunca en `lsusb`/router | cable de solo carga o puerto | cable de DATOS / otro puerto |
| `/status` no responde | WiFi distinto, IP cambiada | revisar SSID/2.4 GHz y reserva DHCP |
| Panel dice "sin señal" | placa desenchufada o WiFi caído | revisar energía de la placa |
| Cámara bloqueada en el teléfono | HTTP sin HTTPS | aceptar certificado o usar HTTPS |
| QR no lee de noche | poca luz | LED de puerta / brillo del ticket |
| Ticket sale sin QR | impresora sin soporte ESC/POS `GS ( k` | actualizar firmware impresora o cambiar modelo |
| Puerta no abre y el relé suena | inversión del pulsador del relé | ajustar `RELAY_ACTIVE_LOW` |
