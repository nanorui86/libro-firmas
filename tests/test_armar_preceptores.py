import os
import tempfile
import unittest
from datetime import date

import openpyxl

import libro_firmas
import preceptores
import render_libro
from tests.test_render_preceptores import _molde

HOY = date(2026, 11, 18)


def _fila(apellido, nombre, **extra):
    base = {"apellido": apellido, "nombre": nombre, "cargo": "Preceptora", "dias": "lunes,martes,miercoles,jueves,viernes",
            "lic_desde": "", "lic_hasta": "", "lic_motivo": "", "en_lista": "si"}
    base.update(extra)
    return base


class ArmarPreceptores(unittest.TestCase):
    def test_genera_un_excel_con_solo_esa_hoja(self):
        with tempfile.TemporaryDirectory() as d:
            molde, datos, salida = os.path.join(d, "m.xlsx"), os.path.join(d, "p.csv"), os.path.join(d, "salida")
            _molde(molde)
            preceptores.guardar(datos, [_fila("Garcia", "Ana"), _fila("Perez", "Beto", dias="viernes")])
            ruta = libro_firmas.armar_preceptores(molde, datos, salida, HOY)
            wb = openpyxl.load_workbook(ruta)
            self.assertEqual(wb.sheetnames, [render_libro.HOJA_PRECEPTORES])
            ws = wb[render_libro.HOJA_PRECEPTORES]
            self.assertEqual((ws["B2"].value, ws["C2"].value), ("GARCIA, Ana", "Preceptora"))
            self.assertEqual(ws["J3"].value, "PEREZ, Beto")  # viernes, tercer bloque

    def test_licencia_vigente_sin_estar_en_lista_no_sale(self):
        with tempfile.TemporaryDirectory() as d:
            molde, datos = os.path.join(d, "m.xlsx"), os.path.join(d, "p.csv")
            _molde(molde)
            preceptores.guardar(datos, [_fila("Garcia", "Ana", lic_motivo="licencia", en_lista="no"), _fila("Perez", "Beto")])
            ws = openpyxl.load_workbook(libro_firmas.armar_preceptores(molde, datos, d, HOY))[render_libro.HOJA_PRECEPTORES]
            self.assertEqual((ws["B2"].value, ws["B3"].value), ("PEREZ, Beto", None))

    def test_sin_preceptores_explica_que_hacer(self):
        with tempfile.TemporaryDirectory() as d:
            molde = os.path.join(d, "m.xlsx")
            _molde(molde)
            with self.assertRaisesRegex(ValueError, "agregalos"):
                libro_firmas.armar_preceptores(molde, os.path.join(d, "no_existe.csv"), d, HOY)

    def test_las_opciones_traen_la_ruta_de_preceptores(self):
        self.assertTrue(libro_firmas.opciones("x.pdf").preceptores.endswith("preceptores.csv"))
        self.assertEqual(libro_firmas.opciones("x.pdf", base="C:\\base", preceptores="p.csv").preceptores, os.path.join("C:\\base", "p.csv"))


if __name__ == "__main__":
    unittest.main()
