# Manual de operación — Sistema de Moteles

Comandos del día a día. Ubicación del proyecto en este equipo:

```
/home/jma/Documents/Proyect/motel-system
```

---

## Arrancar / detener / reiniciar / estado

```bash
cd /home/jma/Documents/Proyect/motel-system

./start.sh      # arranca el servidor (si no existe la base, la siembra con datos demo)
./stop.sh       # detiene el servidor
./restart.sh    # reinicia (stop + start)
./status.sh     # ¿está corriendo? muestra el PID y todas las URLs de acceso
```

Al arrancar en primer plano, los mensajes (check-ins, escaneos, aperturas)
salen por pantalla con hora. Para dejarlo en segundo plano:

```bash
nohup ./start.sh > data/server.log 2>&1 &
```

## Arranque automático con systemd (recomendado en el motel)

```bash
sudo cp deploy/motel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now motel     # queda arrancando solo al encender el PC
```

Gestión con systemd:

```bash
sudo systemctl status motel     # ver estado
sudo systemctl restart motel    # reiniciar
sudo systemctl stop motel       # detener
journalctl -u motel -f          # ver los mensajes en vivo
```

> No mezclar: si el servidor corre por systemd, no usar `./start.sh`.
> Elegir una sola forma de arranque (systemd en producción).

## Ver registros y datos

```bash
tail -f data/server.log                                  # mensajes del servidor (si se usó nohup/systemd)
python3 tools/backup_db.py                               # respaldo inmediato de la base
```

- **DB Browser for SQLite** (en el dock): abrir `data/motel.db` en modo
  *read-only* → tablas y **vistas** (`v_ventas_dia`, `v_ventas_mes`,
  `v_ocupaciones_cabanas`, `v_horarios_semana`).
- Los tickets impresos en modo archivo quedan en `data/tickets/`.

## Respaldo y restauración

- Respaldo manual: `python3 tools/backup_db.py` → copia en `data/backups/`
  (guarda las últimas 30).
- Respaldo automático (cron, cada hora):

```
0 * * * * cd /home/jma/Documents/Proyect/motel-system && python3 tools/backup_db.py >> data/backups/backup.log 2>&1
```

- **Restaurar** un respaldo:

```bash
./stop.sh
cp data/backups/motel_FECHA.db data/motel.db
./start.sh
```

## Pruebas

```bash
python3 tools/smoke_test.py        # recorre TODO el flujo y reporta PASS/FAIL
```

> Ojo: la prueba **genera datos** (check-ins, cobros). Si no quieres eso en la
> base, respaldar antes o limpiar después con `python3 tools/seed_demo.py --reset`
> (BORRA todo y deja las cabañas libres).

## Simulador de placas (sin hardware)

```bash
python3 tools/sim_device.py --id cab01 --port 9081 &
python3 tools/sim_device.py --id gate-01 --port 9099 &
```

## Configuración

- `config.json`: puerto, `require_keys` (claves on/off), `panel_key`,
  impresora (`file` / `network` / `command`).
- HTTPS para cámaras: `./make_cert.sh` (activa `"https": true` solo).
- Los secretos de las placas viven en la tabla `devices` (y en el
  `include/config.h` de cada placa).

## Documentos relacionados

| Documento | Contenido |
|---|---|
| `README.md` | visión general, arquitectura y demo |
| `docs/instalacion.md` | checklist de instalación real (hardware, red, pruebas por cabaña) |
| `docs/urls.md` | catálogo de cada URL: propósito y uso |
| `docs/flujo.md` | reglas de negocio: validación de QR, estados, eventos |
| `docs/piloto.md` | protocolo de piloto con criterios objetivos y conversión automática a orden de compra |
