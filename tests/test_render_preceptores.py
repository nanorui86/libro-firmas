import os
import tempfile
import unittest

import openpyxl
from openpyxl.styles import Border, Font, Side

import render_libro

MED = Side(style="medium")
HOJA = render_libro.HOJA_PRECEPTORES
MOLDE_REAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos", "plantilla_libro.xlsx")


def _molde(ruta):
    wb = openpyxl.Workbook()
    wb.active.title = "otra"
    for nombre in render_libro.HOJAS.values():
        wb.create_sheet(nombre).cell(60, 25).value = "x"  # fuerza el tamaño de la hoja de docentes
    ws = wb.create_sheet(HOJA)
    ws.cell(60, 18).value = "x"
    ws.row_dimensions[1].height, ws.row_dimensions[2].height = 14.25, 34.5
    for r, h in zip(range(25, 31), (34.5, 35.1, 35.1, 35.1, 35.1, 50.25)):
        ws.row_dimensions[r].height = h
    ws.row_dimensions[31].height, ws.row_dimensions[32].height = 18.75, 34.5
    for c0 in (1, 5, 9, 13):
        for k in range(3):
            ws.cell(2, c0 + k).border = Border(left=MED, right=MED, top=MED, bottom=MED)
        ws.cell(1, c0 + 1).font = Font(name="Arial", size=10, bold=True)
    ws.cell(31, 10).font = Font(name="Arial", size=10, bold=True)
    wb.save(ruta)


def _listas(n_por_dia):
    """n_por_dia: cantidad de personas por día (lunes..viernes), con nombres inventados."""
    return [[(f"APELLIDO{d}{i:02d}, Ana", "Preceptora") for i in range(n)] for d, n in enumerate(n_por_dia)]


def _armar(n_por_dia):
    d = tempfile.TemporaryDirectory()
    molde, salida = os.path.join(d.name, "m.xlsx"), os.path.join(d.name, "s.xlsx")
    _molde(molde)
    render_libro.render_solo_preceptores(molde, salida, _listas(n_por_dia))
    ws = openpyxl.load_workbook(salida)[HOJA]
    d.cleanup()
    return ws


class Geometria(unittest.TestCase):
    def test_con_22_personas_queda_como_el_molde(self):
        ws = _armar([22, 22, 22, 22, 19])  # lunes, martes, miércoles, jueves, viernes
        self.assertEqual([ws.cell(1, c).value for c in (2, 6, 10, 14)], ["Lunes", "Martes", "Viernes", "Miércoles"])
        self.assertEqual(ws["B2"].value, "APELLIDO000, Ana")
        self.assertEqual(ws["C2"].value, "Preceptora")
        self.assertEqual(ws["J2"].value, "APELLIDO400, Ana")   # viernes en el tercer bloque
        self.assertEqual(ws["N2"].value, "APELLIDO200, Ana")   # miércoles en el cuarto
        self.assertEqual((ws["A24"].value, ws["A25"].value), (23, None))  # 23 renglones numerados, con o sin persona
        self.assertEqual(ws["B24"].value, None)
        self.assertEqual(ws["J31"].value, "Jueves")
        self.assertEqual((ws["I32"].value, ws["I54"].value, ws["I55"].value), (1, 23, None))
        self.assertEqual(ws["J32"].value, "APELLIDO300, Ana")

    def test_alturas_como_el_molde(self):
        ws = _armar([22] * 5)
        self.assertEqual([ws.row_dimensions[r].height for r in (1, 2, 24)], [14.25, 34.5, 34.5])
        self.assertEqual([ws.row_dimensions[r].height for r in (25, 26, 30, 31, 32)], [34.5, 35.1, 50.25, 18.75, 34.5])

    def test_con_30_personas_la_hoja_crece_y_jueves_baja(self):
        ws = _armar([30, 22, 22, 22, 22])
        self.assertEqual((ws["A31"].value, ws["A32"].value), (30, None))
        self.assertEqual(ws["B31"].value, "APELLIDO029, Ana")
        self.assertEqual(ws["E31"].value, 30)  # los demás bloques también ganan renglones
        self.assertEqual(ws["J38"].value, "Jueves")
        self.assertEqual((ws["I39"].value, ws["I61"].value, ws["I62"].value), (1, 23, None))
        self.assertEqual(ws.row_dimensions[31].height, 34.5)

    def test_con_50_personas_nada_se_pisa(self):
        ws = _armar([22, 22, 22, 22, 50])
        self.assertEqual((ws["I51"].value, ws["I52"].value), (50, None))
        titulo = next(r for r in range(1, 120) if ws.cell(r, 10).value == "Jueves")
        self.assertEqual(titulo, 58)
        self.assertGreater(titulo, 51)

    def test_jueves_con_mas_de_23(self):
        ws = _armar([22, 22, 22, 40, 22])
        self.assertEqual((ws["I71"].value, ws["I72"].value), (40, None))

    def test_borde_medio_en_los_renglones_usados_y_firma_libre(self):
        ws = _armar([22] * 5)
        self.assertEqual(ws["B2"].border.left.style, "medium")
        self.assertEqual(ws["C24"].border.bottom.style, "medium")
        self.assertIsNone(getattr(ws["D2"].border.left, "style", None))

    def test_area_de_impresion_en_dos_tramos_sin_la_columna_p(self):
        self.assertEqual(_armar([22] * 5).print_area.replace("'prec. 2026'!", ""), "$A$1:$H$24,$I$1:$O$54")
        self.assertEqual(_armar([30] * 5).print_area.replace("'prec. 2026'!", ""), "$A$1:$H$31,$I$1:$O$68")

    def test_nombre_largo_se_parte_en_dos_lineas(self):
        ws = _armar([22] * 5)
        self.assertTrue(ws["B2"].alignment.wrap_text)

    def test_listas_vacias(self):
        ws = _armar([0] * 5)
        self.assertEqual((ws["A24"].value, ws["B2"].value, ws["J31"].value), (23, None, "Jueves"))


class Hojas(unittest.TestCase):
    def test_solo_esa_hoja(self):
        with tempfile.TemporaryDirectory() as d:
            molde, salida = os.path.join(d, "m.xlsx"), os.path.join(d, "s.xlsx")
            _molde(molde)
            render_libro.render_solo_preceptores(molde, salida, _listas([1] * 5))
            self.assertEqual(openpyxl.load_workbook(salida).sheetnames, [HOJA])

    def test_el_libro_completo_la_incluye_solo_si_se_pide(self):
        with tempfile.TemporaryDirectory() as d:
            molde, salida = os.path.join(d, "m.xlsx"), os.path.join(d, "s.xlsx")
            _molde(molde)
            docentes = {t: [[("PEREZ, Ana", "Profesora")] for _ in range(5)] for t in render_libro.HOJAS}
            render_libro.render(molde, salida, docentes)
            self.assertNotIn(HOJA, openpyxl.load_workbook(salida).sheetnames)
            render_libro.render(molde, salida, docentes, preceptores=_listas([1] * 5))
            self.assertEqual(openpyxl.load_workbook(salida).sheetnames, list(render_libro.HOJAS.values()) + [HOJA])


@unittest.skipUnless(os.path.exists(MOLDE_REAL), "falta datos/plantilla_libro.xlsx (el molde real no se versiona)")
class ContraElMoldeReal(unittest.TestCase):
    """Con las mismas personas que ya trae la hoja, el resultado es la hoja del molde, celda por celda."""

    def test_22_personas_dan_la_misma_hoja(self):
        original = openpyxl.load_workbook(MOLDE_REAL)[HOJA]
        # bloques en el orden de la hoja: lunes, martes, viernes, miércoles (dias 0, 1, 4, 2) y jueves (3)
        por_dia = {}
        for dia, c0, fila0 in ((0, 1, 2), (1, 5, 2), (4, 9, 2), (2, 13, 2), (3, 9, 32)):
            por_dia[dia] = [(str(original.cell(r, c0 + 1).value).strip(), str(original.cell(r, c0 + 2).value or "").strip())
                            for r in range(fila0, fila0 + 23) if original.cell(r, c0 + 1).value]
        listas = [por_dia[d] for d in range(5)]
        with tempfile.TemporaryDirectory() as d:
            salida = os.path.join(d, "s.xlsx")
            render_libro.render_solo_preceptores(MOLDE_REAL, salida, listas)
            nuevo = openpyxl.load_workbook(salida)[HOJA]
        norma = lambda v: "" if v is None else str(v).strip()  # noqa: E731
        diferentes = [(r, c) for r in range(1, 56) for c in range(1, 17)
                      if norma(original.cell(r, c).value) != norma(nuevo.cell(r, c).value)]
        self.assertEqual(diferentes, [])
        for r in range(1, 55):  # hasta el último renglón de Jueves
            self.assertEqual(original.row_dimensions[r].height, nuevo.row_dimensions[r].height, f"alto de la fila {r}")


if __name__ == "__main__":
    unittest.main()
