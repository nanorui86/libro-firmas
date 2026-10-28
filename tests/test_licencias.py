"""Tests con datos inventados: el repo es público, nada de nombres reales."""
import os
import tempfile
import unittest
from datetime import date

import licencias
import turnos_previos

HOY = date(2026, 10, 28)
ENCABEZADO = "docente;desde;hasta;motivo;en_lista\n"


def _cargar(filas):
    with tempfile.TemporaryDirectory() as d:
        ruta = os.path.join(d, "l.csv")
        open(ruta, "w", encoding="utf-8").write(ENCABEZADO + filas)
        return licencias.cargar(ruta, HOY)


class TestCargar(unittest.TestCase):
    def test_vigente_vencida_futura_y_sin_fin(self):
        g = _cargar(
            "Vega, Eva;2026-09-01;2027-03-01;maternidad;si\n"
            "Roca, Ian;;;enfermedad;si\n"
            "Pino, Ada;2026-01-01;2026-02-01;vieja;si\n"
            "Sol, Leo;2026-12-01;2027-01-01;futura;si\n"
        )
        self.assertEqual([l["docente"] for l in g["vigentes"]], ["Vega, Eva", "Roca, Ian"])
        self.assertEqual([l["docente"] for l in g["sin_fin"]], ["Roca, Ian"])
        self.assertEqual([l["docente"] for l in g["vencidas"]], ["Pino, Ada"])
        self.assertEqual([l["docente"] for l in g["futuras"]], ["Sol, Leo"])

    def test_en_lista_por_defecto_es_si(self):
        g = _cargar("Vega, Eva;;;x;\nRoca, Ian;;;x;no\n")
        self.assertEqual([l["en_lista"] for l in g["vigentes"]], [True, False])

    def test_invalidos_fallan(self):
        for fila in ("Vega, Eva;;;x;quizas\n", "Vega, Eva;2026-05-01;2026-04-01;x;si\n"):
            with self.assertRaises(ValueError):
                _cargar(fila)

    def test_archivo_inexistente_no_es_error(self):
        g = licencias.cargar("no_existe.csv", HOY)
        self.assertEqual(g["vigentes"], [])


def _lic(nombre, clave, en_lista=True):
    return {"docente": nombre, "clave": clave, "en_lista": en_lista}


class TestAplicar(unittest.TestCase):
    PREVIOS = {"Vega, Eva": {0: "tm", 2: "tmyt"}}

    def _previos(self, nombre):
        return (self.PREVIOS.get(nombre, {}), "el último libro generado")

    def test_sin_horario_nuevo_sigue_en_la_lista_con_sus_turnos(self):
        asign = {}
        notas, sin_datos = licencias.aplicar(asign, [_lic("Vega, Eva", "vega eva")], self._previos)
        self.assertEqual(asign, {("vega eva", 0): "tm", ("vega eva", 2): "tmyt"})
        self.assertEqual(sin_datos, [])
        self.assertIn("figura en la lista", notas[0])

    def test_con_clases_en_el_horario_no_se_toca(self):
        asign = {("vega eva", 1): "tm"}
        licencias.aplicar(asign, [_lic("Vega, Eva", "vega eva")], self._previos)
        self.assertEqual(asign, {("vega eva", 1): "tm"})

    def test_en_lista_no_la_saca(self):
        asign = {("vega eva", 1): "tm", ("roca ian", 1): "tm"}
        licencias.aplicar(asign, [_lic("Vega, Eva", "vega eva", en_lista=False)], self._previos)
        self.assertEqual(asign, {("roca ian", 1): "tm"})

    def test_sin_datos_de_turnos_se_avisa_y_no_se_inventa(self):
        asign = {}
        _, sin_datos = licencias.aplicar(asign, [_lic("Roca, Ian", "roca ian")], self._previos)
        self.assertEqual(sin_datos, ["Roca, Ian"])
        self.assertEqual(asign, {})


class TestTurnosPrevios(unittest.TestCase):
    def test_desde_listas_acepta_nombres_o_tuplas(self):
        listas = {"tm": [["Vega, Eva"], [], [("Roca, Ian", "Profesor")], [], []], "tmyt": [[], [], ["Vega, Eva"], [], []]}
        self.assertEqual(turnos_previos.desde_listas(listas),
                         {"Vega, Eva": {0: "tm", 2: "tmyt"}, "Roca, Ian": {2: "tm"}})

    def test_guardar_y_cargar(self):
        listas = {"tm": [[("VEGA, Eva", "Profesora")], [], [], [], []], "tmyt": [[], [], [("VEGA, Eva", "Profesora")], [], []]}
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "t.csv")
            turnos_previos.guardar(listas, ruta)
            self.assertEqual(turnos_previos.cargar(ruta), {"VEGA, Eva": {0: "tm", 2: "tmyt"}})

    def test_buscar_con_ortografia_distinta_y_orden_de_fuentes(self):
        ultimo = ("el último libro generado", {"CASAL, Marlen": {0: "tm"}})
        actual = ("el libro actual", {"CASAL, Marlene": {1: "tmyt"}, "VEGA, Eva": {4: "tm"}})
        self.assertEqual(turnos_previos.buscar("Casal, Marlene", ultimo, actual), ({0: "tm"}, "el último libro generado"))
        self.assertEqual(turnos_previos.buscar("Vega, Eva", ultimo, actual), ({4: "tm"}, "el libro actual"))
        self.assertEqual(turnos_previos.buscar("Nadie, Ana", ultimo, actual), ({}, ""))


if __name__ == "__main__":
    unittest.main()
