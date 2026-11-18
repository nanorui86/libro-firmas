"""Llena las hojas del libro de firmas sobre el molde de Excel.

Solo se escriben N°, nombre y tratamiento. No se toca el zoom (100), las
alturas de fila (renglón del libro físico) ni los márgenes. Los saltos de
página se fijan a mano en las posiciones del original para que no dependan de
la impresora.
"""
from copy import copy

import openpyxl
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
from openpyxl.styles.cell_style import StyleArray
from openpyxl.worksheet.pagebreak import Break

HOJAS = {"tm": "prof. tm 2026", "tmyt": "prof.tmyt.2026"}
PRIMERA_COLUMNA = (1, 5, 9, 13, 17)  # A, E, I, M, Q: N° | nombre | tratamiento | firma
PRIMERA_FILA = 2
RENGLONES_POR_PAGINA = 24
# Saltos del original (verificados con Excel): columnas tras H, P (y V en tm); filas de a 24.
SALTOS_COLUMNA = {"tm": (8, 16, 22), "tmyt": (8, 16)}
PAGINAS_FILAS = {"tm": 1, "tmyt": 2}
# El molde de tm tiene formato (sin datos) hasta la columna W y Excel la imprime como una hoja más, en blanco, después del
# viernes (el libro original también la saca). El área de impresión corta en V, la última columna con renglones.
ULTIMA_COLUMNA_IMPRESION = {"tm": 22}
RENGLONES_PRIMERA_PAGINA = RENGLONES_POR_PAGINA - 1  # la fila 1 es el encabezado del día


# El molde dibuja los bordes celda por celda y a mano: en la fila que se copia, los martes (y los jueves de
# mañana y tarde) tienen líneas finas o abiertas. Todo renglón usado se cierra igual: línea media en las tres
# columnas con datos (N°, nombre, tratamiento); la columna de firma queda libre.
_LADO = Side(style="medium")
_CAJA = Border(left=_LADO, right=_LADO, top=_LADO, bottom=_LADO)


# Los rótulos de día del molde vienen desparejos ("lunes", "    Martes", tamaños y alineaciones distintas).
ROTULOS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")


# Hoja de preceptores: una sola hoja con los cinco días. Lunes, Martes, Viernes y Miércoles van en fila (columnas A, E, I, M; el rótulo
# en la segunda columna de cada bloque) y Jueves debajo, en las columnas I. Cada bloque tiene 23 renglones y crece si hace falta.
HOJA_PRECEPTORES = "prec. 2026"
BLOQUES_PRECEPTORES = ((0, 1, "Lunes"), (1, 5, "Martes"), (4, 9, "Viernes"), (2, 13, "Miércoles"))  # (día 0-4, columna, rótulo)
JUEVES = (3, 9, "Jueves")
RENGLONES_PRECEPTORES = 23
FILAS_ENTRE_BLOQUES = 7  # el rótulo de Jueves va 7 filas debajo del último renglón de arriba (fila 31 cuando hay 23)


class DesbordeError(ValueError):
    pass


def leer_listas(ruta_xlsx):
    """{turno: [lista de nombres impresos por día]} de un libro ya armado."""
    wb = openpyxl.load_workbook(ruta_xlsx, read_only=True)
    listas = {}
    for turno, hoja in HOJAS.items():
        dias = [[] for _ in PRIMERA_COLUMNA]
        for fila in wb[hoja].iter_rows(min_row=PRIMERA_FILA, values_only=True):
            for i, c0 in enumerate(PRIMERA_COLUMNA):
                if len(fila) > c0 and fila[c0] and str(fila[c0]).strip():  # columna del nombre
                    dias[i].append(str(fila[c0]).strip())
        listas[turno] = dias
    return listas


def _estilo(ws, fila, columna):
    return copy(ws.cell(fila, columna)._style)


def _hoja_preceptores(ws, listas):
    """listas: [por día 0-4: [(nombre_impreso, cargo)]] ya ordenadas. Reescribe la hoja con la misma forma que el molde."""
    arriba = max([RENGLONES_PRECEPTORES] + [len(listas[d]) for d, _, _ in BLOQUES_PRECEPTORES])
    abajo = max(RENGLONES_PRECEPTORES, len(listas[JUEVES[0]]))
    alto = lambda fila: ws.row_dimensions[fila].height  # noqa: E731
    alto_renglon, alto_titulo, alto_jueves = alto(2), alto(31), alto(32)
    alto_separacion = [alto(r) for r in range(RENGLONES_PRECEPTORES + 2, RENGLONES_PRECEPTORES + FILAS_ENTRE_BLOQUES + 1)]
    molde = {c0: [_estilo(ws, 2, c0 + k) for k in range(4)] for _, c0, _ in BLOQUES_PRECEPTORES}
    molde_jueves = [_estilo(ws, 32, JUEVES[1] + k) for k in range(4)]
    rotulo = {c0: _estilo(ws, 1, c0 + 1) for _, c0, _ in BLOQUES_PRECEPTORES}
    rotulo_jueves = _estilo(ws, 31, JUEVES[1] + 1)

    ultima = max(ws.max_row, 2 * (arriba + abajo) + 12)
    for r in range(2, ultima + 1):
        ws.row_dimensions[r].height = None
        for c in range(1, 17):
            celda = ws.cell(r, c)
            celda.value = None
            celda._style = StyleArray()

    def bloque(fila0, c0, estilos, filas, renglones, alto_fila):
        for n in range(renglones):
            r = fila0 + n
            ws.row_dimensions[r].height = alto_fila
            for k in range(4):
                celda = ws.cell(r, c0 + k)
                celda._style = copy(estilos[k])
                celda.border = copy(_CAJA) if k < 3 else Border()
            ws.cell(r, c0).value = n + 1
            if n < len(filas):
                ws.cell(r, c0 + 1).value, ws.cell(r, c0 + 2).value = filas[n]
                alineacion = copy(ws.cell(r, c0 + 1).alignment)
                alineacion.wrap_text = True  # un nombre largo se parte en dos líneas en vez de cortarse al imprimir
                ws.cell(r, c0 + 1).alignment = alineacion

    for dia, c0, texto in BLOQUES_PRECEPTORES:
        ws.cell(1, c0 + 1).value = texto
        ws.cell(1, c0 + 1)._style = copy(rotulo[c0])
        bloque(2, c0, molde[c0], listas[dia], arriba, alto_renglon)
    for k, altura in enumerate(alto_separacion):
        ws.row_dimensions[arriba + 2 + k].height = altura
    titulo = arriba + FILAS_ENTRE_BLOQUES + 1
    ws.row_dimensions[titulo].height = alto_titulo
    ws.cell(titulo, JUEVES[1] + 1).value = JUEVES[2]
    ws.cell(titulo, JUEVES[1] + 1)._style = copy(rotulo_jueves)
    bloque(titulo + 1, JUEVES[1], molde_jueves, listas[JUEVES[0]], abajo, alto_jueves)
    # Dos áreas de impresión, cada una en sus páginas: Lunes y Martes (A-H), y Viernes, Miércoles y Jueves (I-O). Sin esto Excel
    # imprime hojas en blanco (la columna P, ancha y sin nada, no entra en el ancho) y deja en una página aparte los números de
    # la columna I (el original también las saca).
    ws.print_area = f"A1:H{arriba + 1},I1:O{titulo + abajo}"


def render_solo_preceptores(plantilla, salida, preceptores):
    """Libro con solo la hoja de preceptores (no necesita el horario de Untis)."""
    wb = openpyxl.load_workbook(plantilla)
    for nombre in wb.sheetnames:
        if nombre != HOJA_PRECEPTORES:
            wb.remove(wb[nombre])
    _hoja_preceptores(wb[HOJA_PRECEPTORES], preceptores)
    wb.save(salida)


def render(plantilla, salida, listas, preceptores=None):
    """listas: {turno: [por día: [(nombre_impreso, tratamiento), ...]]} ya ordenadas.
    preceptores: [por día: [(nombre_impreso, cargo)]] o None (sin la hoja de preceptores)."""
    wb = openpyxl.load_workbook(plantilla)
    conservar = set(HOJAS.values()) | ({HOJA_PRECEPTORES} if preceptores is not None else set())
    for nombre in wb.sheetnames:
        if nombre not in conservar:
            wb.remove(wb[nombre])
    if preceptores is not None:
        _hoja_preceptores(wb[HOJA_PRECEPTORES], preceptores)

    for turno, nombre_hoja in HOJAS.items():
        ws = wb[nombre_hoja]
        ultima = ws.max_row
        for i, c0 in enumerate(PRIMERA_COLUMNA):
            filas = listas[turno][i]
            if PRIMERA_FILA + len(filas) - 1 > ultima:  # no hay renglones para todos
                raise DesbordeError(
                    f"{nombre_hoja}, día {i + 1}: {len(filas)} docentes no entran en las "
                    f"{ultima - PRIMERA_FILA + 1} filas del molde"
                )
            molde = [_estilo(ws, PRIMERA_FILA, c0 + k) for k in range(4)]
            # Como en el original: la primera página siempre lleva todos sus renglones numerados,
            # con o sin docente; a partir de ahí, solo los que hacen falta.
            renglones = max(len(filas), RENGLONES_PRIMERA_PAGINA)
            for r in range(PRIMERA_FILA, ultima + 1):
                n = r - PRIMERA_FILA
                usada = n < renglones
                for k in range(4):
                    celda = ws.cell(r, c0 + k)
                    celda.value = None
                    celda._style = copy(molde[k]) if usada else StyleArray()
                    if usada:
                        celda.border = copy(_CAJA) if k < 3 else Border()
                if usada:
                    ws.cell(r, c0).value = n + 1
                if n < len(filas):
                    ws.cell(r, c0 + 1).value, ws.cell(r, c0 + 2).value = filas[n]
                    # Un nombre largo se parte en dos líneas en vez de cortarse al imprimir.
                    alineacion = copy(ws.cell(r, c0 + 1).alignment)
                    alineacion.wrap_text = True
                    ws.cell(r, c0 + 1).alignment = alineacion

        for rotulo, c0 in zip(ROTULOS, PRIMERA_COLUMNA):
            celda = ws.cell(1, c0)
            celda.value = rotulo
            celda.font = Font(name="Arial", size=12, bold=True)
            celda.alignment = Alignment(horizontal="left", vertical="center")

        if turno in ULTIMA_COLUMNA_IMPRESION:
            ws.print_area = f"A1:{get_column_letter(ULTIMA_COLUMNA_IMPRESION[turno])}{ultima}"
        ws.row_breaks.brk = []
        ws.col_breaks.brk = []
        for k in range(1, PAGINAS_FILAS[turno] + 1):
            ws.row_breaks.append(Break(id=RENGLONES_POR_PAGINA * k))
        for c in SALTOS_COLUMNA[turno]:
            ws.col_breaks.append(Break(id=c))
    wb.save(salida)
