"""Generate docs/diagramas/finsage-flujo.drawio (two pages) for the Week 13 presentation."""

import sys
from html import escape
from pathlib import Path
from xml.sax.saxutils import quoteattr

OUT = Path(sys.argv[1])

# Palette
INK = "#1F2328"
MUTED = "#5E6670"
DONE = ("#E4F2E7", "#2F7D3B")
READY = ("#FBF0DC", "#9A6412")
TODO = ("#F1F0EC", "#8E8B85")
PHASE = {
    "doc": ("#EEF1F6", "#3E5F8A"),
    "ffp": ("#E6F4F3", "#0B6E69"),
    "mpr": ("#EAF0FB", "#2D5DA8"),
    "drr": ("#F1ECFA", "#6A4BA8"),
    "gen": ("#FBEFE6", "#B5602C"),
    "ui": ("#F3F3F1", "#3C3B37"),
    "eval": ("#FFF7E6", "#9A6412"),
}
STATUS = {"done": DONE, "ready": READY, "todo": TODO}


class Page:
    def __init__(self, name: str):
        self.name = name
        self.cells: list[str] = []
        self.n = 1

    def _id(self) -> str:
        self.n += 1
        return f"c{self.n}"

    def text(self, x, y, w, h, html, size=12, color=INK, align="left", bold=False, parent="1"):
        cid = self._id()
        style = (f"text;html=1;whiteSpace=wrap;align={align};verticalAlign=middle;fontSize={size};"
                 f"fontColor={color};fontFamily=Helvetica;{'fontStyle=1;' if bold else ''}")
        self._vertex(cid, html, style, x, y, w, h, parent)
        return cid

    def box(self, x, y, w, h, html, status="todo", parent="1", size=11, fill=None, stroke=None, dashed=False):
        cid = self._id()
        f, s = STATUS[status] if fill is None else (fill, stroke)
        style = (f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};strokeWidth=1.4;"
                 f"fontColor={INK};fontSize={size};fontFamily=Helvetica;align=left;verticalAlign=top;"
                 f"spacingLeft=8;spacingRight=8;spacingTop=6;{'dashed=1;' if dashed else ''}")
        self._vertex(cid, html, style, x, y, w, h, parent)
        return cid

    def lane(self, x, y, w, h, title, phase):
        cid = self._id()
        f, s = PHASE[phase]
        style = (f"swimlane;html=1;startSize=44;rounded=1;arcSize=4;whiteSpace=wrap;fillColor={s};swimlaneFillColor={f};"
                 f"strokeColor={s};fontColor=#FFFFFF;fontSize=13;fontStyle=1;fontFamily=Helvetica;collapsible=0;")
        self._vertex(cid, title, style, x, y, w, h, "1")
        return cid

    def pill(self, x, y, w, h, label, fill, stroke, parent="1"):
        cid = self._id()
        style = (f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontSize=10;"
                 f"fontColor={INK};fontFamily=Helvetica;")
        self._vertex(cid, label, style, x, y, w, h, parent)
        return cid

    def edge(self, src, dst, label="", dashed=False, exit=None, entry=None, color=MUTED):
        cid = self._id()
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;strokeWidth=1.6;"
                 f"strokeColor={color};fontSize=10;fontColor={MUTED};{'dashed=1;' if dashed else ''}")
        if exit:
            style += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(label)} style="{style}" edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        return cid

    def _vertex(self, cid, value, style, x, y, w, h, parent):
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(value)} style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )

    def xml(self, page_w, page_h):
        body = "".join(self.cells)
        return (
            f'<diagram name={quoteattr(self.name)} id="{escape(self.name.lower().replace(" ", "_"))}">'
            f'<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
            f'fold="1" page="1" pageScale="1" pageWidth="{page_w}" pageHeight="{page_h}" background="#FFFFFF" math="0" shadow="0">'
            f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram>'
        )


def step(title, body, note=None, figure=None):
    parts = [f"<b>{title}</b>", f"<span style='color:{MUTED}'>{body}</span>"]
    if figure:
        parts.append(f"<b style='color:#0B6E69'>{figure}</b>")
    if note:
        parts.append(f"<i style='color:{MUTED};font-size:10px'>{note}</i>")
    return "<br>".join(parts)


# ---------------------------------------------------------------- page 1: full workflow
p1 = Page("1 Flujo FinSage")
p1.text(40, 20, 1500, 40, "FinSage: RAG por varias vías para reportes financieros", size=26, bold=True)
p1.text(40, 62, 1600, 26,
        "Réplica del paper de Wang et al. (CIKM 2025) sobre un documento de trabajo: el 10-K 2022 de AMD, tomado de FinanceBench",
        size=14, color=MUTED)

# Phase 0: document
d = p1.lane(40, 120, 230, 560, "0. Documento", "doc")
d1 = p1.box(15, 60, 200, 120, step("FinanceBench", "Banco público de preguntas sobre reportes de empresas de EE. UU. Cada pregunta trae su respuesta correcta y la página de evidencia."), parent=d, status="done")
d2 = p1.box(15, 205, 200, 160, step("10-K 2022 de AMD", "Reporte anual en PDF con texto, tablas y notas financieras.", figure="121 páginas<br>7 preguntas de prueba"), parent=d, status="done")
d3 = p1.box(15, 390, 200, 150, step("Por qué este documento", "Sus preguntas mezclan buscar un dato, calcular y razonar, y la evidencia está repartida por todo el reporte."), parent=d, status="done", fill="#FFFFFF", stroke="#C9CDD3", dashed=True)
p1.edge(d1, d2)

# Phase 1: FFP
f = p1.lane(300, 120, 360, 960, "1. FFP: preparación del documento (una sola vez)", "ffp")
f1 = p1.box(15, 60, 330, 110, step("1.1 Lectura por página", "El PDF se convierte en texto página por página. Las tablas se conservan como tablas.", note="Réplica: pymupdf4llm. Paper: MinerU", figure="121 páginas, 61 tablas"), parent=f, status="done")
f2 = p1.box(15, 190, 330, 150, step("1.2 Fragmentación", "El texto se corta en pedazos de hasta 256 tokens. Ningún pedazo cruza de página. Cada título abre una sección nueva. Las tablas largas se parten por filas y cada parte repite el encabezado de columnas.", figure="670 fragmentos"), parent=f, status="done")
f3 = p1.box(15, 360, 330, 100, step("1.3 Vectores de significado", "Cada fragmento se convierte en un vector con BGE-M3, para buscar por significado y no solo por palabras."), parent=f, status="done")
f4 = p1.box(15, 480, 330, 130, step("1.4 Quitar duplicados", "Si dos fragmentos son casi iguales (similitud de 0.98 o más) se queda el primero. El que queda recuerda en qué otras páginas estaba su copia.", figure="598 fragmentos"), parent=f, status="done")
f5 = p1.box(15, 630, 330, 130, step("1.5 Resumen de cada sección", "Un modelo de lenguaje resume cada sección en dos oraciones y ese resumen se pega a todos sus fragmentos como contexto.", note="Modelo: gpt-6-luna", figure="261 secciones"), parent=f, status="ready")
f6 = p1.box(15, 780, 330, 160, step("1.6 Tres índices", "<b>Palabras</b>: BM25<br><b>Significado</b>: FAISS con los vectores<br><b>Resúmenes</b>: vectores de los resúmenes de sección"), parent=f, status="todo")
for a, b in [(f1, f2), (f2, f3), (f3, f4), (f4, f5), (f5, f6)]:
    p1.edge(a, b)
p1.edge(d2, f1, exit=(1, 0.5), entry=(0, 0.5))

# Phase 2: MPR
m = p1.lane(690, 120, 420, 960, "2. MPR: búsqueda por cuatro vías (en cada pregunta)", "mpr")
m1 = p1.box(15, 60, 390, 80, step("2.1 Pregunta en el chat", "La pregunta llega junto con el historial de la conversación."), parent=m, status="todo")
m2 = p1.box(15, 160, 390, 100, step("2.2 Reescritura", "Un modelo de lenguaje divide la pregunta en subpreguntas completas, reemplaza pronombres y agrega el contexto del historial."), parent=m, status="todo")
v_y, v_h, v_w = 285, 150, 88
mb = p1.box(15, v_y, v_w, v_h, step("BM25", "Busca las palabras exactas"), parent=m, status="todo", size=10)
md = p1.box(15 + 100, v_y, v_w, v_h, step("Densa", "Busca por significado con los vectores"), parent=m, status="todo", size=10)
mm = p1.box(15 + 200, v_y, v_w, v_h, step("Metadatos", "Busca en los resúmenes de sección"), parent=m, status="todo", size=10)
mh = p1.box(15 + 300, v_y, v_w, v_h, step("HyDE", "Inventa una respuesta posible y busca textos parecidos a ella"), parent=m, status="todo", size=10)
p1.text(15, 440, 390, 30, "Las cuatro vías corren en paralelo y cada una encuentra evidencia distinta", size=10, color=MUTED, align="center", parent=m)
m4 = p1.box(15, 480, 390, 110, step("2.3 Unión y expansión", "Se juntan los hallazgos de las cuatro vías y cada fragmento suma a sus vecinos de página si son parecidos.", note="Umbral 0.85 y hasta 5 vecinos, como en el paper"), parent=m, status="todo")
p1.edge(m1, m2)
for v in (mb, md, mm, mh):
    p1.edge(m2, v)
    p1.edge(v, m4)
p1.edge(f6, mb, dashed=True, label="índices", exit=(1, 0.5), entry=(0, 0.5), color="#0B6E69")
m5 = p1.box(15, 620, 390, 140, step("Paper frente a réplica", "HyDE en el paper usa Qwen 7B ajustado con datos propios. En la réplica HyDE usa gpt-6-luna sin ajuste, porque los datos de ajuste no se publicaron."), parent=m, status="done", fill="#FFFFFF", stroke="#C9CDD3", dashed=True)

# Phase 3: DRR
r = p1.lane(1140, 120, 260, 560, "3. DRR: reordenamiento", "drr")
r1 = p1.box(15, 60, 230, 170, step("3.1 Reranker", "Un segundo modelo lee cada candidato junto a la pregunta y los ordena por relevancia real, no solo por parecido.", figure="Top 5 por subpregunta"), parent=r, status="todo")
r2 = p1.box(15, 255, 230, 140, step("Paper frente a réplica", "El paper entrena su reranker con DPO. La réplica usa bge-reranker-v2-m3 ya entrenado, porque el modelo del paper no se publicó."), parent=r, status="done", fill="#FFFFFF", stroke="#C9CDD3", dashed=True)
p1.edge(m4, r1, exit=(1, 0.5), entry=(0, 0.5))

# Phase 4: generation
g = p1.lane(1430, 120, 260, 560, "4. Respuesta", "gen")
g1 = p1.box(15, 60, 230, 150, step("4.1 Generación con cita", "El modelo responde usando solo los 5 fragmentos elegidos y cita la página de cada dato.", note="Modelo: gpt-6-luna"), parent=g, status="todo")
g2 = p1.box(15, 235, 230, 110, step("4.2 Fusión", "Si hubo varias subpreguntas, sus respuestas se unen en una sola."), parent=g, status="todo")
p1.edge(r1, g1, exit=(1, 0.5), entry=(0, 0.5))
p1.edge(g1, g2)

# Phase 5: chatbot
u = p1.lane(1720, 120, 270, 560, "5. Chatbot visual", "ui")
u1 = p1.box(15, 60, 240, 115, step("Respuesta en vivo", "El texto aparece mientras se genera, con cada cita como un botón."), parent=u, status="done")
u2 = p1.box(15, 195, 240, 115, step("Panel: cómo lo encontré", "Muestra en vivo las subpreguntas, lo que trajo cada vía y el top del reranker."), parent=u, status="done")
u3 = p1.box(15, 330, 240, 100, step("Visor del PDF", "Al tocar una cita se abre el reporte en la página citada."), parent=u, status="done")
u4 = p1.box(15, 450, 240, 90, step("Corridas grabadas", "Respaldo para la exposición con corridas reales guardadas."), parent=u, status="done")
p1.edge(g2, u1, exit=(1, 0.5), entry=(0, 0.5))

# Phase 6: evaluation band
e = p1.lane(1140, 710, 850, 370, "6. Evaluación (espejo de las tablas del paper)", "eval")
e1 = p1.box(15, 60, 260, 200, step("A. Aporte de cada vía", "Se agrega una vía por vez: densa, luego BM25, metadatos, HyDE y expansión.", figure="Mide si la página de evidencia aparece entre lo encontrado", note="Tabla 1 del paper"), parent=e, status="todo")
e2 = p1.box(295, 60, 260, 200, step("B. FinSage frente a RAG simple", "Mismo modelo en los dos. Un juez de otra familia (Qwen local) decide si cada respuesta es correcta.", figure="Exactitud y acierto de la página citada", note="Tabla 2 del paper"), parent=e, status="todo")
e3 = p1.box(575, 60, 260, 200, step("C. Tiempo y costo", "Segundos, tokens y dólares de cada etapa por pregunta.", note="Tabla 3 del paper"), parent=e, status="todo")
p1.text(15, 275, 820, 60, "Con 7 preguntas los resultados se leen pregunta por pregunta y se comparan con el paper de forma cualitativa.", size=11, color=MUTED, parent=e)
p1.edge(g2, e2, dashed=True, exit=(0.5, 1), entry=(0.5, 0))

# Legend
p1.text(40, 710, 230, 24, "Estado", size=13, bold=True)
p1.pill(40, 740, 230, 30, "Hecho y probado", *DONE)
p1.pill(40, 780, 230, 30, "Programado, listo para correr", *READY)
p1.pill(40, 820, 230, 30, "Pendiente", *TODO)
p1.pill(40, 860, 230, 30, "Nota: paper frente a réplica", "#FFFFFF", "#C9CDD3")

# ---------------------------------------------------------------- page 2: one question, end to end
p2 = Page("2 Recorrido de una pregunta")
p2.text(40, 20, 1600, 40, "Recorrido de una pregunta real por el sistema", size=26, bold=True)
p2.text(40, 62, 1700, 26, "Pregunta de FinanceBench sobre el 10-K 2022 de AMD: ¿AMD reportó concentración de clientes en el año fiscal 2022?", size=14, color=MUTED)

a = p2.lane(40, 120, 1880, 250, "Antes de cualquier pregunta: el documento se prepara una vez", "ffp")
a1 = p2.box(15, 60, 270, 170, step("Página 12 del PDF", "Sección de clientes del reporte, con texto corrido y el dato buscado."), parent=a, status="done")
a2 = p2.box(310, 60, 340, 170, step("Fragmento AMD_2022_10K:11:0", "Sección: Customers<br>105 tokens, solo de la página 12<br><br><span style='color:#1F2328'>“One customer accounted for 16% of our consolidated net revenue for the year ended December 31, 2022.”</span>"), parent=a, status="done")
a3 = p2.box(675, 60, 260, 170, step("Vector BGE-M3", "El fragmento se convierte en un vector de 1024 números que representa su significado."), parent=a, status="done")
a4 = p2.box(960, 60, 280, 170, step("Sin duplicado", "No tiene copias casi iguales en el reporte, así que se conserva tal cual. Queda entre los 598 fragmentos finales."), parent=a, status="done")
a5 = p2.box(1265, 60, 270, 170, step("Resumen de la sección", "Un modelo resume la sección Customers y ese resumen viaja como contexto pegado al fragmento."), parent=a, status="ready")
a6 = p2.box(1560, 60, 300, 170, step("Tres índices", "El fragmento queda buscable por sus palabras, por su significado y por el resumen de su sección."), parent=a, status="todo")
for x, y in [(a1, a2), (a2, a3), (a3, a4), (a4, a5), (a5, a6)]:
    p2.edge(x, y, exit=(1, 0.5), entry=(0, 0.5))

b = p2.lane(40, 420, 1880, 290, "Cuando llega la pregunta: RAG por cuatro vías", "mpr")
b1 = p2.box(15, 60, 250, 210, step("Pregunta", "<span style='color:#1F2328'>“Did AMD report customer concentration in FY22?”</span>"), parent=b, status="todo")
b2 = p2.box(290, 60, 260, 210, step("Reescritura", "Queda como una subpregunta completa, con empresa y año explícitos, lista para buscar."), parent=b, status="todo")
b3 = p2.box(575, 60, 310, 210, step("Cuatro vías", "<b>BM25</b> encuentra las palabras customer y revenue<br><b>Densa</b> encuentra el significado<br><b>Metadatos</b> encuentra la sección Customers<br><b>HyDE</b> imagina una respuesta y busca textos parecidos"), parent=b, status="todo")
b4 = p2.box(910, 60, 260, 210, step("Reranker", "Ordena los candidatos y el fragmento de la página 12 debería quedar primero entre los 5 elegidos."), parent=b, status="todo")
b5 = p2.box(1195, 60, 320, 210, step("Respuesta con cita", "El modelo responde solo con esos 5 fragmentos y cita la página.<br><br><b>Respuesta esperada según FinanceBench</b><br><span style='color:#1F2328'>Sí, un cliente representó el 16% de los ingresos netos consolidados.</span><br>Evidencia: página 12"), parent=b, status="todo")
b6 = p2.box(1540, 60, 320, 210, step("Chatbot", "La respuesta aparece en vivo. La cita es un botón que abre el PDF en la página 12, junto al extracto citado.<br><br>Así se puede comprobar con los propios ojos que el dato está en el documento."), parent=b, status="done")
for x, y in [(b1, b2), (b2, b3), (b3, b4), (b4, b5), (b5, b6)]:
    p2.edge(x, y, exit=(1, 0.5), entry=(0, 0.5))
p2.edge(a6, b3, dashed=True, label="los índices alimentan la búsqueda", exit=(0.5, 1), entry=(0.5, 0), color="#0B6E69")

p2.text(40, 735, 230, 24, "Estado", size=13, bold=True)
p2.pill(40, 763, 200, 28, "Hecho y probado", *DONE)
p2.pill(260, 763, 220, 28, "Programado, listo para correr", *READY)
p2.pill(500, 763, 140, 28, "Pendiente", *TODO)

xml = ('<?xml version="1.0" encoding="UTF-8"?>'
       '<mxfile host="Electron" agent="finsage-replica" version="24.0.0">'
       + p1.xml(2040, 1120) + p2.xml(1960, 820) + "</mxfile>")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(xml, encoding="utf-8")
print(f"wrote {OUT} ({len(xml)} chars)")
