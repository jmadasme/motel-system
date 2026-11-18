# Protocolo de Piloto — criterios objetivos y conversión automática a orden de compra

> **Regla de oro:** nada se decide por sensaciones. Todas las puertas de
> entrada y salida del piloto son medibles, y el resultado se calcula con el
> propio sistema. Si el puntaje cumple, la orden de compra se emite
> automáticamente; si no cumple, no se emite y ambas partes quedan cubiertas.
> **Este documento se firma ANTES de instalar nada.**

---

## 1. Alcance del piloto (completar antes de firmar)

| Concepto | Valor |
|---|---|
| Cliente / sede | ______________________________ |
| Dirección | ______________________________ |
| Cabañas incluidas en el piloto | ______ (ej. 4 de 12) |
| Duración | ______ días (recomendado: 21 días = 3 semanas) |
| Fecha de instalación | ____ / ____ / ________ |
| Fecha de evaluación | ____ / ____ / ________ |
| Contraparte técnica del cliente | ______________________________ |

Queda explícito: **las cabañas fuera del piloto no se ven afectadas** y
continúan con su operación actual.

---

## 2. Qué aporta cada parte

| Proveedor (nosotros) | Cliente |
|---|---|
| Servidor central configurado (PC Linux) | Espacio, energía y UPS en recepción |
| Firmware de placas + puesta en marcha | Acceso para instalar en las cabañas del piloto |
| Capacitación a recepción y cocina (2 h) | 2 teléfonos Android por cabaña del piloto (o los que tenga) |
| Panel, ingresos y respaldos automáticos | Personal disponible para la medición semanal |
| Soporte por el período del piloto | Datos históricos firmados (ver sección 4) |

**Hardware que el piloto requiere comprar** (queda instalado en la sede):
cerraduras eléctricas 12 V con fuente, cableado, y (si no se usa un PC del
cliente) el mini-PC del servidor.

---

## 3. Costos del piloto y crédito (completar antes de firmar)

| Ítem | Monto | Paga | Nota |
|---|---|---|---|
| Cerraduras eléctricas + fuentes (____ unidades) | $ ____________ | Cliente | Quedan instaladas; si no convierte, se pagan al costo |
| Cableado y materiales | $ ____________ | Cliente | |
| Mini-PC + UPS (si se deja uno dedicado) | $ ____________ | Cliente | Alternativa: comodato y se retira si no convierte |
| Instalación y capacitación | $ ____________ | Proveedor | Aporte al piloto |
| Soporte del período | $ ____________ | Proveedor | |
| **Crédito por conversión** | Todo lo aportado por el proveedor se **acredita** a la orden de compra final |

Si el piloto **no** cumple los criterios (sección 6), no hay orden de compra,
no hay penalidades para nadie, y el cliente conserva el hardware instalado
pagando solo su costo. El mini-PC en comodato se retira en 7 días.

---

## 4. Línea base firmada (antes de instalar)

Para poder comparar hay que fijar el "antes" **con firma del cliente**:

| Dato (últimos 30 días) | Valor declarado |
|---|---|
| Ingresos de caja registrados por noche (promedio) | $ ____________ |
| Ocupaciones declaradas por noche (promedio) | ______ |
| Ticket promedio | $ ____________ |
| Pedidos de cocina facturados (si se lleva registro) | ______ |

Firma línea base: Cliente ______________  Proveedor ______________

---

## 5. Métricas: cómo las produce el propio sistema

Todas salen de la base `motel.db` (tabla `events`, `tickets`, `orders`,
`devices`) y del panel/Excel. Nada se mide "de memoria".

| ID | Métrica | Fuente | Ventana de medición |
|---|---|---|---|
| C1 | Disponibilidad de puertas (uptime de placas) | heartbeats en `devices.last_seen` | todo el piloto |
| C2 | Escaneos correctos: QR del cliente rechazado por error | `events` (scan_ok vs scan_denegado) | todo el piloto |
| C3 | Registro completo: cada cobro del libro de caja tiene su ticket | reconciliación semanal `tickets` vs libro | semanal, con firma |
| C4 | Accesos por puerta sin ticket (incluye aperturas manuales) | `events`: `puerta` sin `scan_ok` asociado, `panel/open` | todo el piloto |
| C5 | Operación continua (funciona sin internet / con cortes) | uptime del servidor + bitácora | todo el piloto |
| C6 | Cobros completos: total = base + consumos en cada salida | `tickets.total_charged` vs desglose | todas las salidas |
| N1 | Delta de recaudación declarada vs línea base | libro + `v_ventas_dia` | mismo día de semana, promedio |
| N2 | Uso del kiosco de pedidos | `orders` por estadía | todo el piloto |
| N3 | Tiempo de check-in | hora `checkin` vs hora de impresión | primeras 2 semanas |

---

## 6. Umbrales, puntaje y regla de decisión

**Críticos** (si uno queda bajo el 60 % de su puntaje, no hay orden aunque el
total llegue a 80):

| ID | Criterio | Umbral | Peso |
|---|---|---|---|
| C1 | Disponibilidad de puertas | ≥ 98 % | 10 |
| C2 | Escaneos correctos (sin rechazos indebidos) | ≥ 98 % | 10 |
| C3 | Registro completo vs libro de caja | 100 % | 20 |
| C4 | Accesos sin ticket | **0** (manuales justificadas al 100 %) | 20 |
| C5 | Operación continua | sin caídas > 1 h | 5 |
| C6 | Cobros completos (base + consumos) | 100 % | 10 |
| **Comerciales** | | | |
| N1 | Delta de recaudación declarada | ≥ +15 % promedio | 15 |
| N2 | Kiosco usado | ≥ 25 % de estadías con pedido | 5 |
| N3 | Tiempo de check-in | ≤ 90 s | 5 |
| | | **Total** | **100** |

**Regla automática (sin interpretación):**

> **Puntaje total ≥ 80 Y todos los críticos ≥ 60 % de su peso → se emite la
> orden de compra por el 100 % de las cabañas de la sede, dentro de 72 horas.**
>
> Cualquier otro resultado → **no se emite orden**. Opciones acordadas: (a)
> extender el piloto UNA vez por 14 días solo si el fallo fue técnico y ya
> corregido, o (b) cierre del piloto con el cliente pagando solo el hardware
> al costo.

El puntaje lo calcula una planilla única que firma ambas partes al cierre
(sección 8). Las "opiniones" no puntúan.

---

## 7. Calendario tipo (referencia)

| Momento | Actividad |
|---|---|
| Día −7 | Firma de este protocolo + línea base |
| Día 1 | Instalación, capacitación, prueba por cabaña (checklist) |
| Día 3 | Compactación: primera revisión de bitácora con el cliente |
| Día 7 / 14 | Reconciliación semanal: tickets vs libro de caja (firma) |
| Día 21 | Cierre: sesión de medición, puntaje y veredicto automático |
| Día 24 | Si cumple: orden de compra emitida (plantilla anexo A) |

---

## 8. Hoja de cierre del piloto (firmable)

| ID | Métrica | Resultado | ¿Cumple? | Puntaje obtenido |
|---|---|---|---|---|
| C1 | Disponibilidad de puertas | ____ % | ☐ | ____ / 10 |
| C2 | Escaneos correctos | ____ % | ☐ | ____ / 10 |
| C3 | Registro completo vs libro | ____ % | ☐ | ____ / 20 |
| C4 | Accesos sin ticket | ____ | ☐ | ____ / 20 |
| C5 | Operación continua | ____ | ☐ | ____ / 5 |
| C6 | Cobros completos | ____ % | ☐ | ____ / 10 |
| N1 | Delta recaudación | ____ % | ☐ | ____ / 15 |
| N2 | Uso kiosco | ____ % | ☐ | ____ / 5 |
| N3 | Check-in | ____ s | ☐ | ____ / 5 |
| | **TOTAL** | | | **____ / 100** |

Críticos ≥ 60 % de su peso: ☐ Sí ☐ No

**Veredicto automático:**
☐ TOTAL ≥ 80 y críticos OK → **SE EMITE ORDEN DE COMPRA**
☐ Caso contrario → **NO SE EMITE**

Firmas: Cliente ______________  Proveedor ______________  Fecha ____/____/____

---

## Anexo A — Plantilla de orden de compra (referencia)

> **ORDEN DE COMPRA N.º ____** — Fecha: ____/____/____
> Cliente: ____________________  Sede: ____________________
> Detalle: Sistema de control para ____ cabañas (hardware + instalación +
> capacitación + soporte ____ meses), conforme al Protocolo de Piloto firmado.
> Monto: $ ____________  (se acredita el valor del piloto: − $ ____________)
> **Total a pagar: $ ____________**
> Firmas: Cliente ______________  Proveedor ______________

---

## Anexo B — Frases para la reunión (por si ayudan)

- "El piloto no se aprueba con opiniones: se aprueba con esta planilla."
- "Si el sistema cumple, la compra ya está acordada: usted no decide
  *si* compra, solo *cuándo* arrancamos con todas las cabañas."
- "Si no cumple, usted no compró promesas: se quedó con el hardware al costo."
