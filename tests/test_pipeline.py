"""Tests con datos inventados: el repo es público, nada de nombres reales."""
import csv
import os
import tempfile
import unittest
from datetime import date

import openpyxl
from openpyxl.styles import Alignment, Border, Side

import excepciones
import libro_firmas
import maestro
import parse_horario
import render_libro
from clasificar import clave_docente
from parse_horario import Docente


def _chars(texto, size, x0=50.0):
    return [{"text": c, "size": size, "x0": x0 + i * 5} for i, c in enumerate(texto)]


class TestCabecera(unittest.TestCase):
    def test_celular_pegado_a_las_horas(self):
        # En el PDF real el celular (negrita 10.8) y las horas (18) quedan pegados.
        chars = (_chars("Lopez, Ana", 13.5) + _chars("Casa: 4000-0000 / Celular: 15-38252197", 10.8, 300)
                 + _chars("2.00", 18.0, 500) + _chars("Horas", 18.0, 530))
        self.assertEqual(parse_horario.nombre_y_horas(chars), ("Lopez, Ana", "2.00"))

    def test_nombre_superpuesto_con_el_contacto(self):
        chars = _chars("Gomez Lima, Ma. Alejand", 13.5) + _chars("C", 10.8, 200) + _chars("ra", 13.5, 205)
        chars += _chars("asa: 4000-0000", 10.8, 220) + _chars("9.00", 18.0, 500)
        self.assertEqual(parse_horario.nombre_y_horas(chars), ("Gomez Lima, Ma. Alejandra", "9.00"))

    def test_sin_horas_legibles(self):
        self.assertEqual(parse_horario.nombre_y_horas(_chars("Perez, Beto", 13.5)), ("Perez, Beto", ""))


class TestMaestro(unittest.TestCase):
    def test_nombre_impreso(self):
        self.assertEqual(maestro.nombre_impreso("Garcia Lima; Ana"), "GARCIA LIMA, Ana")
        self.assertEqual(maestro.nombre_impreso("Perez ,  Beto"), "PEREZ, Beto")

    def test_misma_persona_con_ortografia_distinta(self):
        self.assertTrue(maestro.misma_persona("Casal, Marlene", "CASAL, Marlen"))
        self.assertTrue(maestro.misma_persona("Lopez Brun, Nico", "LOPEZ BRUHN, Nico"))
        self.assertFalse(maestro.misma_persona("Perez, Ana", "Perez, Beto"))

    def test_tratamiento_unico_y_ambiguo(self):
        fuente = [({"perez"}, {"ana"}, "Profesora"), ({"perez"}, {"ana", "maria"}, "Profesor")]
        self.assertEqual(maestro.buscar_tratamiento("Perez, Ana", fuente), "")  # ambiguo: no se adivina
        self.assertEqual(maestro.buscar_tratamiento("Perez, Ana", fuente[:1]), "Profesora")
        self.assertEqual(maestro.buscar_tratamiento("Otro, Ana", fuente), "")

    def test_completar_no_adivina_y_frena(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "docentes.csv")
            _, sin, _ = maestro.completar_maestro(["Perez, Ana"], ruta, os.path.join(d, "no_existe.csv"))
            self.assertEqual(sin, ["Perez, Ana"])


class TestExcepciones(unittest.TestCase):
    def _archivo(self, d, filas):
        ruta = os.path.join(d, "ex.csv")
        excepciones.escribir(filas, ruta)
        return ruta

    def _fila(self, **kw):
        base = {"docente": "Perez, Ana", "dias": "lunes,martes", "turno": "tm", "desde": "", "hasta": "", "motivo": "x"}
        return dict(base, **kw)

    def test_vigente_vencida_futura_y_sin_fin(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = self._archivo(d, [
                self._fila(),
                self._fila(docente="Venc, Uno", hasta="2026-10-01"),
                self._fila(docente="Fut, Dos", desde="2026-12-01"),
                self._fila(docente="Fin, Tres", hasta="2026-11-30"),
            ])
            vig, venc, fut, sin_fin = excepciones.cargar(ruta, date(2026, 10, 28))
            self.assertEqual([e["docente"] for e in vig], ["Perez, Ana", "Fin, Tres"])
            self.assertEqual([e["docente"] for e in venc], ["Venc, Uno"])
            self.assertEqual([e["docente"] for e in fut], ["Fut, Dos"])
            self.assertEqual([e["docente"] for e in sin_fin], ["Perez, Ana"])

    def test_aplicar_agrega_cambia_y_quita(self):
        asign = {("perez ana", 0): "tmyt", ("gomez beto", 1): "tm"}
        vig = [{"clave": "perez ana", "dias": ["lunes"], "turno": "tm"},
               {"clave": "lopez cris", "dias": ["viernes"], "turno": "tmyt"},
               {"clave": "gomez beto", "dias": ["martes"], "turno": "quitar"}]
        self.assertEqual(excepciones.aplicar(asign, vig), {("perez ana", 0): "tm", ("lopez cris", 4): "tmyt"})

    def test_dia_invalido_falla(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = self._archivo(d, [self._fila(dias="sabado")])
            with self.assertRaises(ValueError):
                excepciones.cargar(ruta, date(2026, 10, 28))


class TestAsignacionYListas(unittest.TestCase):
    def test_mixto_dia_a_dia(self):
        doc = Docente("Perez, Ana", "5.0", {(0, 1), (0, 2), (1, 3), (1, 9)})
        asign = libro_firmas.asignar([doc])
        self.assertEqual(asign, {("perez ana", 0): "tm", ("perez ana", 1): "tmyt"})

    def test_orden_ignora_tildes_y_mayusculas(self):
        maes = {k: {"impreso": i, "tratamiento": "Profesor"} for k, i in
                {"alamo z": "ÁLAMO, Z", "alamo b": "ALAMO, B", "avila c": "AVILA, C"}.items()}
        asign = {(k, 0): "tm" for k in maes}
        orden = [n for n, _ in libro_firmas.armar_listas(asign, maes)["tm"][0]]
        self.assertEqual(orden, ["ALAMO, B", "ÁLAMO, Z", "AVILA, C"])

    def test_emparejar_nombres_parecidos(self):
        quitan, agregan = libro_firmas._emparejar(["CASAL, Marlen", "RIOS, Ana"], ["CASAL, Marlene", "VEGA, Eva"])
        self.assertEqual((quitan, agregan), (["RIOS, Ana"], ["VEGA, Eva"]))


class TestRender(unittest.TestCase):
    def _plantilla(self, d, filas=40):
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        borde = Border(bottom=Side(style="medium"))
        for hoja in render_libro.HOJAS.values():
            ws = wb.create_sheet(hoja)
            for r in range(1, filas + 1):
                ws.row_dimensions[r].height = 34
                for c0 in render_libro.PRIMERA_COLUMNA:
                    for k in range(4):
                        ws.cell(r, c0 + k).border = borde
                        ws.cell(r, c0 + 1).alignment = Alignment(vertical="center")
        wb.create_sheet("otra hoja")
        ruta = os.path.join(d, "molde.xlsx")
        wb.save(ruta)
        return ruta

    def _listas(self, n_por_dia):
        return {t: [[(f"APELLIDO{i}, Nombre", "Profesor") for i in range(n)] for n in n_por_dia]
                for t in ("tm", "tmyt")}

    def test_numera_la_primera_pagina_entera_y_conserva_alturas(self):
        with tempfile.TemporaryDirectory() as d:
            salida = os.path.join(d, "s.xlsx")
            render_libro.render(self._plantilla(d), salida, self._listas([2, 0, 30, 1, 5]))
            wb = openpyxl.load_workbook(salida)
            self.assertEqual(wb.sheetnames, list(render_libro.HOJAS.values()))  # solo las dos hojas
            ws = wb["prof. tm 2026"]
            self.assertEqual(ws["A2"].value, 1)
            self.assertEqual(ws["B2"].value, "APELLIDO0, Nombre")
            self.assertEqual(ws["C2"].value, "Profesor")
            self.assertEqual(ws["B4"].value, None)           # renglón vacío...
            self.assertEqual(ws["A24"].value, 23)            # ...pero numerado hasta cerrar la página
            self.assertIsNone(ws["A25"].value)               # martes vacío: nada más allá de la página
            self.assertEqual(ws["I31"].value, 30)            # miércoles: 30 docentes pasan a la 2.ª página
            self.assertEqual(ws.row_dimensions[2].height, 34)
            self.assertTrue(ws["B2"].alignment.wrap_text)    # nombre largo: se parte, no se corta

    def test_saltos_de_pagina_fijos(self):
        with tempfile.TemporaryDirectory() as d:
            salida = os.path.join(d, "s.xlsx")
            render_libro.render(self._plantilla(d), salida, self._listas([1] * 5))
            wb = openpyxl.load_workbook(salida)
            self.assertEqual([b.id for b in wb["prof. tm 2026"].col_breaks.brk], [8, 16, 22])
            self.assertEqual([b.id for b in wb["prof.tmyt.2026"].row_breaks.brk], [24, 48])

    def test_desborde_falla_en_vez_de_cortar(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(render_libro.DesbordeError):
                render_libro.render(self._plantilla(d, filas=10), os.path.join(d, "s.xlsx"), self._listas([20, 0, 0, 0, 0]))


if __name__ == "__main__":
    unittest.main()
