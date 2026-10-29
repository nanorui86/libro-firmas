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


def render(plantilla, salida, listas):
    """listas: {turno: [por día: [(nombre_impreso, tratamiento), ...]]} ya ordenadas."""
    wb = openpyxl.load_workbook(plantilla)
    for nombre in wb.sheetnames:
        if nombre not in HOJAS.values():
            wb.remove(wb[nombre])

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
