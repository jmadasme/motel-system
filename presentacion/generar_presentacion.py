#!/usr/bin/env python3
"""Genera la presentacion comercial PREMIUM (PPTX) del sistema de moteles.

Uso:  python3 presentacion/generar_presentacion.py
Salida: presentacion/Sistema_Moteles_Presentacion.pptx
Capturas: presentacion/capturas/*.png (paginas maqueta del sistema)
"""

import io
import os

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

BASE = os.path.dirname(os.path.abspath(__file__))
CAPS = os.path.join(BASE, "capturas")
OUT = os.path.join(BASE, "Sistema_Moteles_Presentacion.pptx")

# ---------------------------------------------------------------- paleta
G1 = RGBColor(0x0C, 0x10, 0x18)      # fondo degradado inicial
G2 = RGBColor(0x11, 0x1E, 0x33)      # fondo degradado final
CARD = RGBColor(0x16, 0x1B, 0x26)
CARD2 = RGBColor(0x1E, 0x25, 0x33)
LINE = RGBColor(0x2E, 0x3A, 0x50)
ACC = RGBColor(0x3B, 0x82, 0xF6)
ACC2 = RGBColor(0x60, 0xA5, 0xFA)
OK = RGBColor(0x22, 0xC5, 0x5E)
WARN = RGBColor(0xF5, 0x9E, 0x0B)
BAD = RGBColor(0xEF, 0x44, 0x44)
TXT = RGBColor(0xEC, 0xF1, 0xF8)
MUT = RGBColor(0x94, 0xA3, 0xB8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Calibri"
FONT_LIGHT = "Calibri Light"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 16
N = {"n": 0}


# ---------------------------------------------------------------- utilidades
def slide():
    s = prs.slides.add_slide(BLANK)
    N["n"] += 1
    back = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                              prs.slide_width, prs.slide_height)
    back.fill.gradient()
    stops = back.fill.gradient_stops
    stops[0].color.rgb = G1
    stops[0].position = 0.0
    if len(stops) > 2:
        stops[1].color.rgb = G1
        stops[1].position = 0.5
    stops[-1].color.rgb = G2
    stops[-1].position = 1.0
    try:
        back.fill.gradient_angle = 25
    except Exception:
        pass
    back.line.fill.background()
    back.shadow.inherit = False
    return s


def soft_shadow(shape, blur=140000, dist=45000, alpha=42000):
    try:
        spPr = shape._element.spPr
    except AttributeError:
        return
    for el in spPr.findall(qn("a:effectLst")):
        spPr.remove(el)
    xml = (
        '<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:outerShdw blurRad="{blur}" dist="{dist}" dir="5400000" rotWithShape="0">'
        f'<a:srgbClr val="000000"><a:alpha val="{alpha}"/></a:srgbClr>'
        "</a:outerShdw></a:effectLst>")
    spPr.append(etree.fromstring(xml))


def rect(s, x, y, w, h, fill, line=None, rounded=True, radius=0.055,
         line_w=1.0, shadow=False):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if shadow:
        soft_shadow(shp)
    return shp


def text(s, x, y, w, h, items, size=14, color=TXT, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6,
         font=FONT, line_spacing=1.04):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    first = True
    for it in items:
        if isinstance(it, str):
            it = {"t": it}
        lines = it["t"].split("\n")
        for j, chunk in enumerate(lines):
            if first:
                p = tf.paragraphs[0]
                first = False
            else:
                p = tf.add_paragraph()
            p.alignment = it.get("align", align)
            p.space_after = Pt(it.get("space", space))
            p.line_spacing = it.get("line", line_spacing)
            r = p.add_run()
            r.text = chunk
            r.font.size = Pt(it.get("size", size))
            r.font.bold = it.get("bold", bold)
            r.font.color.rgb = it.get("color", color)
            r.font.name = it.get("font", font)
    return tb


def page_num(s):
    text(s, 11.5, 6.95, 1.15, 0.35,
         [{"t": f"{N['n']:02d} / {TOTAL}", "size": 10.5, "color": MUT,
           "align": PP_ALIGN.RIGHT}])


def footer(s, label="Sistema de Control para Moteles"):
    rect(s, 0.65, 6.98, 12.03, 0.016, LINE, rounded=False)
    text(s, 0.65, 7.06, 8.5, 0.32, [{"t": label, "size": 10, "color": MUT}])
    page_num(s)


def head(s, kicker, title, accent=ACC, kicker_color=None):
    text(s, 0.65, 0.42, 10.5, 0.32,
         [{"t": kicker, "size": 12.5, "bold": True,
           "color": kicker_color or accent}])
    text(s, 0.65, 0.74, 12.1, 0.85, [{"t": title, "size": 26, "bold": True,
                                      "font": FONT_LIGHT}])
    rect(s, 0.68, 1.55, 0.85, 0.05, accent, rounded=False)


def chip(s, x, y, t, color=ACC, fill=None, size=10.5):
    w = 0.16 * len(t) + 0.34
    rect(s, x, y, w, 0.34, fill or CARD2, color, radius=0.5)
    text(s, x, y + 0.015, w, 0.31, [{"t": t, "size": size, "color": color,
                                    "align": PP_ALIGN.CENTER}],
         anchor=MSO_ANCHOR.MIDDLE)
    return x + w + 0.15


def bullets(s, x, y, w, items, size=14.5, color=TXT, accent=ACC,
            gap=0.62, bullet="•"):
    yy = y
    for it in items:
        rect(s, x, yy + 0.08, 0.09, 0.09, accent, rounded=False)
        text(s, x + 0.28, yy - 0.045, w - 0.28, 1.0,
             [{"t": it, "size": size, "color": color, "space": 0}])
        yy += gap
    return yy


def rounded_shot(name, crop_top=40, radius=26):
    from PIL import Image, ImageDraw
    im = Image.open(os.path.join(CAPS, name)).convert("RGBA")
    im = im.crop((0, crop_top, im.width, im.height))
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1],
                                           radius=radius, fill=255)
    im.putalpha(mask)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf, w / h


def shot(s, name, x, y, w, rotation=0, shadow=True, crop_top=40):
    buf, ar = rounded_shot(name, crop_top=crop_top)
    pic = s.shapes.add_picture(buf, Inches(x), Inches(y), width=Inches(w))
    pic.rotation = rotation
    if shadow:
        soft_shadow(pic, blur=160000, dist=60000, alpha=50000)
    return pic, w / ar  # alto aproximado sin rotacion


def screen_slide(kicker, title, items, png, url, who, accent=ACC):
    s = slide()
    head(s, kicker, title, accent)
    x = chip(s, 0.65, 1.85, url, ACC)
    chip(s, x, 1.85, who, MUT)
    bullets(s, 0.68, 2.55, 4.3, items, size=13.5, accent=accent)
    shot(s, png, 5.45, 1.45, 7.3)
    footer(s)


# ================================================================ 1 PORTADA
s = slide()
rect(s, 0, 0, 0.22, 7.5, ACC, rounded=False)
text(s, 0.9, 1.15, 6.3, 0.35,
     [{"t": "P R O P U E S T A   ·   O C T U B R E   2 0 2 6", "size": 12.5,
       "bold": True, "color": ACC2}])
text(s, 0.88, 1.62, 6.6, 2.2, [
    {"t": "SISTEMA DE CONTROL\nINTEGRAL PARA\nMOTELES", "size": 37,
     "bold": True, "font": FONT_LIGHT, "space": 2, "line": 0.95}])
rect(s, 0.92, 3.95, 2.2, 0.05, ACC, rounded=False)
text(s, 0.9, 4.2, 6.2, 1.5, [
    {"t": "Cada ingreso registrado. Cada puerta con QR válido. "
          "La recaudación, en vivo.", "size": 16.5, "color": TXT, "space": 8},
    {"t": "Control de accesos, ocupación y consumos para cadenas de moteles, "
          "con hardware económico y sin mensualidades.", "size": 12.5,
     "color": MUT}])
for i, (a, b) in enumerate([("100 %", "de ingresos\nregistrados"),
                            ("1 s", "QR → puerta\nabierta"),
                            ("$ 0", "costo mensual\nde plataforma")]):
    x = 0.9 + i * 2.12
    text(s, x, 6.05, 2.0, 0.95, [
        {"t": a, "size": 21, "bold": True, "color": ACC2, "space": 1,
         "font": FONT_LIGHT},
        {"t": b, "size": 10.5, "color": MUT, "space": 0, "line": 1.0}])
    if i:
        rect(s, x - 0.28, 6.08, 0.014, 0.85, LINE, rounded=False)
shot(s, "ingresos.png", 7.75, 0.75, 5.6, rotation=-5)
shot(s, "panel.png", 8.15, 2.75, 5.15, rotation=4)
shot(s, "recepcion.png", 7.6, 4.45, 5.45, rotation=-2)

# ================================================================ 2 PROBLEMA
s = slide()
head(s, "01  ·  EL PROBLEMA", "Recaudación que no llega a caja", BAD)
bullets(s, 0.68, 1.95, 7.3, [
    "Cuando el dueño no está, el personal deja entrar parejas sin declararlas "
    "y se queda con ese dinero, a veces en colusión con recepción.",
    "Sin ticket ni registro no hay forma de auditar cuántas parejas entraron, "
    "a qué hora ni cuánto se cobró.",
    "Cámaras y confianza no bastan: hace falta que cada peso pase por el "
    "sistema, automáticamente.",
    "El efectivo sin trazabilidad se pierde en silencio, todas las noches, "
    "en todas las cabañas.",
], size=14, accent=BAD)
rect(s, 8.35, 1.75, 4.35, 4.4, CARD, BAD, line_w=1.5, shadow=True)
text(s, 8.7, 2.0, 3.7, 3.9, [
    {"t": "¿CUÁNTO SE PIERDE?", "size": 12, "bold": True, "color": MUT,
     "space": 10},
    {"t": "20 % – 50 %", "size": 34, "bold": True, "color": BAD,
     "font": FONT_LIGHT, "space": 4},
    {"t": "de la recaudación puede quedar fuera de caja con personal coludido.",
     "size": 12.5, "space": 14},
    {"t": "Más de $1.000.000 al mes", "size": 17, "bold": True,
     "color": WARN, "space": 2},
    {"t": "en un motel de 8 cabañas, en escenario conservador.", "size": 12.5,
     "color": MUT}])
footer(s)

# ================================================================ 3 SOLUCIÓN
s = slide()
head(s, "02  ·  LA SOLUCIÓN", "El ticket QR es la llave — y todo queda registrado", OK)
pasos = [
    ("01", "Recepción registra", "Cabaña y tiempo. El sistema imprime el ticket QR y abre la barrera."),
    ("02", "El cliente escanea", "En la puerta de SU cabaña, un teléfono en kiosco lee el QR."),
    ("03", "El servidor valida", "Ticket activo, no vencido, de esa cabaña. Comando firmado (HMAC)."),
    ("04", "La puerta abre", "La NodeMCU activa el relé 1 s. Todo queda en la bitácora con hora."),
]
for i, (num, t1, t2) in enumerate(pasos):
    x = 0.62 + i * 3.13
    rect(s, x, 1.9, 2.9, 2.55, CARD, ACC if i == 0 else LINE,
         line_w=1.6 if i == 0 else 1.0, shadow=True)
    text(s, x + 0.25, 2.05, 2.4, 0.5, [{"t": num, "size": 20, "bold": True,
                                        "color": ACC2, "font": FONT_LIGHT}])
    text(s, x + 0.25, 2.62, 2.45, 1.7, [
        {"t": t1, "size": 14, "bold": True, "space": 5},
        {"t": t2, "size": 11, "color": MUT, "line": 1.05}])
    if i < 3:
        rect(s, x + 2.93, 2.98, 0.17, 0.42, ACC, rounded=False)
text(s, 0.62, 4.85, 12.1, 1.9, [
    {"t": "Y además, sin esfuerzo extra:", "size": 14.5, "bold": True,
     "space": 8},
    {"t": "•  Pedidos de la cabaña (kiosco interior): se cargan solos a la cuenta.   "
          "•  Botón interior: salida de emergencia 5 s, siempre operativo.",
     "size": 12.5, "color": TXT, "space": 6},
    {"t": "•  Cobro de salida con total exacto (base + consumos).                          "
          "•  Aperturas manuales también registradas: nadie abre “de palabra”.",
     "size": 12.5, "color": TXT}])
footer(s)

# ================================================================ 4 ARQUITECTURA
s = slide()
head(s, "03  ·  LA ARQUITECTURA", "Hardware simple, red interna, cero nube")
rect(s, 0.62, 1.85, 3.15, 1.15, CARD, LINE, shadow=True)
text(s, 0.87, 2.0, 2.75, 0.9, [{"t": "Teléfono PUERTA", "size": 14.5,
                                "bold": True},
                               {"t": "escáner QR · kiosco", "size": 11,
                                "color": MUT}])
rect(s, 0.62, 4.75, 3.15, 1.15, CARD, LINE, shadow=True)
text(s, 0.87, 4.9, 2.75, 0.9, [{"t": "Teléfono INTERIOR", "size": 14.5,
                                "bold": True},
                               {"t": "mini kiosco de pedidos", "size": 11,
                                "color": MUT}])
rect(s, 5.15, 3.05, 3.1, 1.7, CARD2, ACC, line_w=2.0, shadow=True)
text(s, 5.4, 3.3, 2.6, 1.25, [
    {"t": "SERVIDOR CENTRAL", "size": 14.5, "bold": True, "color": ACC2,
     "align": PP_ALIGN.CENTER, "space": 3},
    {"t": "PC Linux · base de datos\npanel en vivo · respaldos", "size": 10.5,
     "color": MUT, "align": PP_ALIGN.CENTER}])
rect(s, 9.55, 1.85, 3.2, 1.15, CARD, LINE, shadow=True)
text(s, 9.8, 2.0, 2.8, 0.9, [{"t": "NodeMCU por cabaña", "size": 14.5,
                              "bold": True},
                             {"t": "relé + chapa 12 V", "size": 11,
                              "color": MUT}])
rect(s, 9.55, 4.75, 3.2, 1.15, CARD, LINE, shadow=True)
text(s, 9.8, 4.9, 2.8, 0.9, [{"t": "NodeMCU barrera", "size": 14.5,
                              "bold": True},
                             {"t": "ingreso y salida del motel", "size": 11,
                              "color": MUT}])
rect(s, 5.15, 5.55, 3.1, 0.8, CARD, LINE, shadow=True)
text(s, 5.4, 5.66, 2.6, 0.6, [{"t": "Impresora térmica", "size": 12.5,
                               "bold": True},
                              {"t": "ticket con QR (ESC/POS)", "size": 10,
                               "color": MUT}])
for (x1, y1, x2, y2) in [(3.85, 2.42, 5.05, 3.9), (3.85, 5.32, 5.05, 4.0),
                         (8.33, 3.9, 9.47, 2.5), (8.33, 4.1, 9.47, 5.2),
                         (6.7, 5.45, 6.7, 4.85)]:
    arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x1), Inches(y1),
                               Inches(max(x2 - x1, 0.28)), Inches(max(y2 - y1, 0.26)))
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = LINE
    arrow.line.fill.background()
    arrow.shadow.inherit = False
text(s, 5.15, 2.55, 3.1, 0.35,
     [{"t": "RED WiFi INTERNA · 2.4 GHz", "size": 11.5, "bold": True,
       "color": WARN, "align": PP_ALIGN.CENTER}])
text(s, 0.62, 6.45, 12.1, 0.5, [
    {"t": "Los comandos servidor → placa van firmados (HMAC-SHA256) con "
          "anti-repetición: nadie en la red puede abrir puertas.",
     "size": 11.5, "color": MUT}])
footer(s)

# ================================================================ 5-10 PANTALLAS
screen_slide("04  ·  OPERACIÓN", "Recepción — el ingreso, en segundos",
             ["Registrar ingreso: cabaña, tiempo (3/6/12 h) y patente.",
              "Imprime el ticket QR y abre la barrera automáticamente.",
              "Todas las cabañas a la vista: estado, tiempo restante y total.",
              "Cobrar salida con base + servicios, sin cuentas a mano.",
              "Reimpresión y aperturas manuales: siempre en bitácora."],
             "recepcion.png", "/recepcion", "mostrador", ACC)

screen_slide("05  ·  OPERACIÓN", "Escáner de puerta — solo abre un ticket válido",
             ["Teléfono Android en kiosco frente a cada puerta.",
              "Lee el QR y consulta al servidor al instante.",
              "Un ticket de otra cabaña o vencido es rechazado con motivo.",
              "Cada intento (bueno o malo) queda en la bitácora.",
              "Plan B: código manual de 6 letras impreso en el ticket."],
             "escaner.png", "/scan?cab=N", "teléfono puerta", ACC)

screen_slide("06  ·  OPERACIÓN", "Catálogo — el mini kiosco de la cabaña",
             ["El cliente pide alimentos y bebidas desde el teléfono interior.",
              "El pedido llega al instante a cocina y se carga a su cuenta.",
              "Catálogo editable: bebidas, comidas, desayuno y más.",
              "Botón “Abrir para salir (5 s)”: salidas rápidas sin esperar.",
              "Nada consumido queda fuera del cobro final."],
             "cabana.png", "/cabana?cab=N", "teléfono interior", ACC)

screen_slide("07  ·  OPERACIÓN", "Cocina — pedidos que no se pierden",
             ["Cola por estados: recibido → preparando → listo → entregado.",
              "Aviso sonoro al entrar un pedido nuevo.",
              "Historial de entregados y cancelaciones controladas.",
              "Cada pedido queda ligado a su cabaña y suma a la cuenta."],
             "cocina.png", "/kitchen", "cocina", WARN)

screen_slide("08  ·  SUPERVISIÓN", "Panel — el motel en vivo",
             ["Ocupación al instante: libres, ocupadas, transcurrido y restante.",
              "Recaudación en curso y pedidos pendientes en la cabecera.",
              "Estado de cada NodeMCU: en línea o sin señal (mantenimiento).",
              "Bitácora completa: check-ins, escaneos, aperturas, salidas.",
              "Provisionar teléfonos: la URL exacta de cada cabaña."],
             "panel.png", "/dashboard", "supervisión", ACC)

screen_slide("09  ·  DINERO", "Ingresos — la plata clara, todos los días",
             ["Cobrado hoy y del mes, separado en base y servicios.",
              "Gráfico de 14 días y lo que se cobrará al salir (en curso).",
              "Historial de cobros por cabaña con fechas y totales.",
              "Descarga Excel (.xlsx) con Resumen, EnCurso y Cobros.",
              "Vistas SQL: día, mes, ocupaciones y horas más cargadas."],
             "ingresos.png", "/ingresos", "dueño / admin", OK)

# ================================================================ 11 HARDWARE
s = slide()
head(s, "10  ·  INSTALACIÓN", "Qué se necesita (ejemplo: 8 cabañas)", WARN)
izq = [("Computador central", "Mini-PC Linux + UPS. Corre servidor, base y panel."),
       ("2 teléfonos por cabaña", "Android económico: puerta (QR) e interior (kiosco)."),
       ("1 NodeMCU por puerta", "Relé + chapa eléctrica 12 V con fuente propia.")]
der = [("1 NodeMCU para barrera", "Apertura automática en ingreso y salida."),
       ("Impresora térmica ESC/POS", "En recepción; QR nativo, sin imágenes."),
       ("Red WiFi interna", "Router + APs 2.4 GHz, red dedicada del sistema.")]
for i, (t1, t2) in enumerate(izq):
    y = 1.95 + i * 1.52
    rect(s, 0.62, y, 5.9, 1.3, CARD, LINE, shadow=True)
    text(s, 0.95, y + 0.16, 5.3, 1.0, [
        {"t": t1, "size": 15, "bold": True, "color": ACC2, "space": 3},
        {"t": t2, "size": 12, "color": TXT}])
for i, (t1, t2) in enumerate(der):
    y = 1.95 + i * 1.52
    rect(s, 6.9, y, 5.9, 1.3, CARD, LINE, shadow=True)
    text(s, 7.23, y + 0.16, 5.3, 1.0, [
        {"t": t1, "size": 15, "bold": True, "color": ACC2, "space": 3},
        {"t": t2, "size": 12, "color": TXT}])
text(s, 0.62, 6.42, 12.1, 0.5,
     [{"t": "Escala proporcional (20 cabañas = 40 teléfonos y 21 NodeMCU). "
           "Lista de compras y montaje paso a paso en docs/instalacion.md.",
       "size": 11.5, "color": MUT}])
footer(s)

# ================================================================ 12 SEGURIDAD
s = slide()
head(s, "11  ·  SEGURIDAD", "Anti-fraude de fábrica", OK)
items = [
    ("Ticket único por ingreso", "Nace en recepción, con hora límite y cabaña. No existe la apertura “de palabra”."),
    ("Solo su cabaña, solo su hora", "Un ticket en otra puerta o fuera de plazo se rechaza y queda registrado con motivo."),
    ("Comandos firmados (HMAC)", "Servidor → placa firmado y con anti-repetición: nadie en la red abre puertas."),
    ("Bitácora de todo", "Check-ins, escaneos, aperturas manuales, salidas de emergencia y pedidos, con hora."),
    ("Sin internet, sin nube", "Opera 100 % en la red interna: sin mensualidades ni datos afuera."),
    ("Respaldos automáticos", "Copia horaria de la base, 30 versiones retenidas y restauración en un comando."),
]
for i, (t1, t2) in enumerate(items):
    col, row = i % 2, i // 2
    x = 0.62 + col * 6.3
    y = 1.9 + row * 1.62
    rect(s, x, y, 6.0, 1.45, CARD, LINE, shadow=True)
    text(s, x + 0.3, y + 0.13, 5.45, 1.2, [
        {"t": t1, "size": 14, "bold": True, "color": OK, "space": 3},
        {"t": t2, "size": 11.5, "color": TXT, "line": 1.0}])
text(s, 0.62, 6.75, 12.1, 0.4,
     [{"t": "Opcional en producción: claves por pantalla y por cabaña, "
           "activables con un interruptor (require_keys).", "size": 11.5,
       "color": MUT}])
footer(s)

# ================================================================ 13 BENEFICIOS
s = slide()
head(s, "12  ·  EL NEGOCIO", "Por qué conviene", ACC2)
for i, (a, b) in enumerate([("100 %", "de los ingresos\ntrazados y auditables"),
                            ("0", "mensualidades:\nsoftware propio"),
                            ("-40 %", "de tiempo de\nrecepción por auto")]):
    x = 0.62 + i * 4.13
    rect(s, x, 1.9, 3.9, 1.7, CARD, ACC, line_w=1.2, shadow=True)
    text(s, x + 0.3, 2.05, 3.3, 1.4, [
        {"t": a, "size": 30, "bold": True, "color": ACC2, "font": FONT_LIGHT,
         "space": 2},
        {"t": b, "size": 12, "color": TXT, "line": 1.0}])
bullets(s, 0.68, 4.0, 12.0, [
    "El dueño ve ocupación, consumo y cobros en vivo desde cualquier PC del motel.",
    "Comida y bebidas: un ingreso extra que antes no se cobraba, ahora se suma solo.",
    "Vistas SQL y Excel listos para contabilidad y para detectar anomalías a tiempo.",
    "Escala sin dolor: más cabañas o más sedes con el mismo sistema.",
], size=14, accent=ACC2, gap=0.6)
footer(s)

# ================================================================ 14 ESTADO
s = slide()
head(s, "13  ·  ESTADO DEL PROYECTO", "Construido, probado y documentado", OK)
est = [
    ("Software completo", "Servidor, recepción, escáner, kiosco, cocina, panel e ingresos. Flujo verificado punta a punta."),
    ("Firmware NodeMCU", "Relé, botón de salida, anti-repetición y latido. Listo para flashear."),
    ("Documentación", "Instalación paso a paso, catálogo de URLs, operación y reglas del flujo."),
    ("Maquetas navegables", "Todas las pantallas con datos de ejemplo para mostrar sin tocar la base."),
    ("Simulador de placas", "Demos y capacitación sin necesidad de hardware instalado."),
    ("Guía de compras", "Materiales y cantidades exactas según número de cabañas."),
]
for i, (t1, t2) in enumerate(est):
    col, row = i % 3, i // 3
    x = 0.62 + col * 4.13
    y = 1.95 + row * 2.4
    rect(s, x, y, 3.95, 2.1, CARD, LINE, shadow=True)
    text(s, x + 0.28, y + 0.2, 3.45, 1.75, [
        {"t": t1, "size": 15, "bold": True, "color": OK, "space": 5},
        {"t": t2, "size": 11.5, "color": TXT, "line": 1.05}])
footer(s)

# ================================================================ 15 ROADMAP
s = slide()
head(s, "14  ·  HOJA DE RUTA", "Próximos pasos sugeridos", WARN)
rect(s, 1.15, 1.95, 0.02, 4.6, LINE, rounded=False)
road = [
    ("Fase 1 — Sede piloto", "Instalación, capacitación del personal y una semana de operación acompañada."),
    ("Fase 2 — Pagos", "Cobro con tarjeta/QR y cierre de caja por turno con reportes por operador."),
    ("Fase 3 — Multi-sede", "Servidor central para varias sedes (PostgreSQL) y reportes consolidados."),
    ("Fase 4 — Extras", "App Android nativa opcional, cartelería digital y fidelización de clientes."),
]
for i, (t1, t2) in enumerate(road):
    y = 1.95 + i * 1.2
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(1.06), Inches(y + 0.32),
                             Inches(0.2), Inches(0.2))
    dot.fill.solid()
    dot.fill.fore_color.rgb = WARN if i == 0 else LINE
    dot.line.fill.background()
    dot.shadow.inherit = False
    rect(s, 1.55, y, 11.1, 1.05, CARD, LINE, shadow=True)
    text(s, 1.85, y + 0.12, 10.6, 0.85, [
        {"t": t1, "size": 14.5, "bold": True, "color": WARN, "space": 2},
        {"t": t2, "size": 11.5, "color": TXT, "line": 1.0}])
footer(s)

# ================================================================ 16 CIERRE
s = slide()
rect(s, 0, 0, 13.333, 0.16, ACC, rounded=False)
text(s, 0.9, 1.55, 11.5, 1.7, [
    {"t": "¿Agendamos una demo en vivo?", "size": 38, "bold": True,
     "font": FONT_LIGHT, "space": 12},
    {"t": "10 minutos: registramos un ingreso, abrimos una puerta con el QR "
          "y vemos la recaudación subir en el panel.", "size": 16,
     "color": MUT}])
rect(s, 0.9, 3.6, 6.2, 2.5, CARD, LINE, shadow=True)
text(s, 1.2, 3.82, 5.7, 2.1, [
    {"t": "INCLUYE", "size": 12.5, "bold": True, "color": ACC2, "space": 8},
    {"t": "•  Demo funcional del sistema completo", "size": 12.5, "space": 5},
    {"t": "•  Maquetas de todas las pantallas", "size": 12.5, "space": 5},
    {"t": "•  Guía de instalación y lista de compras", "size": 12.5, "space": 5},
    {"t": "•  Presupuesto de hardware según cabañas", "size": 12.5}])
rect(s, 7.6, 3.6, 4.85, 2.5, CARD, LINE, shadow=True)
text(s, 7.9, 3.82, 4.3, 2.1, [
    {"t": "CONTACTO", "size": 12.5, "bold": True, "color": ACC2, "space": 8},
    {"t": "Nombre:  _____________________", "size": 12.5, "space": 10},
    {"t": "Teléfono:  ____________________", "size": 12.5, "space": 10},
    {"t": "Correo:  ______________________", "size": 12.5}])
text(s, 0.9, 6.6, 11.0, 0.5,
     [{"t": "Sistema de Control para Moteles · demo funcional incluida · "
           "octubre 2026", "size": 11, "color": MUT}])

prs.save(OUT)
print("Presentacion generada:", OUT)
print("Slides:", len(prs.slides._sldIdLst))
