import os
import tempfile
import unittest
from datetime import date

import maestro
import repositorio


class Fechas(unittest.TestCase):
    def test_ida_y_vuelta(self):
        self.assertEqual(repositorio.fecha_a_iso("28/10/2026"), "2026-10-28")
        self.assertEqual(repositorio.iso_a_fecha("2026-10-28"), "28/10/2026")

    def test_formas_alternativas(self):
        self.assertEqual(repositorio.fecha_a_iso("1-2-27"), "2027-02-01")
        self.assertEqual(repositorio.fecha_a_iso(""), "")

    def test_fecha_invalida(self):
        for malo in ("31/02/2026", "mañana", "2026"):
            with self.assertRaises(ValueError):
                repositorio.fecha_a_iso(malo)


class Licencias(unittest.TestCase):
    def test_validar_normaliza(self):
        lic = repositorio.validar_licencia(
            {"docente": " Perez, Ana ", "desde": "01/09/2026", "hasta": "", "motivo": "x", "en_lista": ""})
        self.assertEqual(lic, {"docente": "Perez, Ana", "desde": "2026-09-01", "hasta": "", "motivo": "x", "en_lista": "si"})

    def test_rechaza_desde_posterior(self):
        with self.assertRaises(ValueError):
            repositorio.validar_licencia({"docente": "A, B", "desde": "02/01/2027", "hasta": "01/01/2027"})

    def test_rechaza_sin_docente(self):
        with self.assertRaises(ValueError):
            repositorio.validar_licencia({"docente": " ", "desde": "", "hasta": ""})

    def test_guardar_y_leer(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "licencias.csv")
            repositorio.guardar_licencias(ruta, [{"docente": "Perez, Ana", "desde": "01/09/2026", "hasta": "01/03/2027",
                                                  "motivo": "licencia por maternidad", "en_lista": "si"}])
            self.assertEqual(repositorio.leer_licencias(ruta)[0]["hasta"], "2027-03-01")

    def test_guardar_invalida_no_toca_el_archivo(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "licencias.csv")
            repositorio.guardar_licencias(ruta, [{"docente": "A, B", "desde": "", "hasta": ""}])
            antes = open(ruta, encoding="utf-8").read()
            with self.assertRaises(ValueError):
                repositorio.guardar_licencias(ruta, [{"docente": "", "desde": "", "hasta": ""}])
            self.assertEqual(open(ruta, encoding="utf-8").read(), antes)

    def test_estados(self):
        hoy = date(2026, 10, 28)
        estado = lambda desde, hasta: repositorio.estado_licencia({"desde": desde, "hasta": hasta}, hoy)
        self.assertEqual(estado("2026-11-01", ""), "Todavía no empezó")
        self.assertEqual(estado("2026-01-01", "2026-10-27"), "Vencida")
        self.assertEqual(estado("2026-01-01", ""), "Vigente, sin fecha de fin")
        self.assertEqual(estado("", "2026-12-01"), "Vigente")

    def test_el_csv_guardado_lo_lee_licencias(self):
        import licencias
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "licencias.csv")
            repositorio.guardar_licencias(ruta, [{"docente": "Perez, Ana", "desde": "01/09/2026", "hasta": "01/03/2027",
                                                  "motivo": "", "en_lista": "no"}])
            grupos = licencias.cargar(ruta, date(2026, 10, 28))
            self.assertEqual(len(grupos["vigentes"]), 1)
            self.assertFalse(grupos["vigentes"][0]["en_lista"])


class Manuales(unittest.TestCase):
    def test_compacta_modulos(self):
        fila = repositorio.validar_manual({"docente": "A, B", "dia": "Lunes", "modulos": "3,2,1, 8-9"})
        self.assertEqual(fila, {"docente": "A, B", "dia": "lunes", "modulos": "1-3,8-9"})

    def test_modulo_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            repositorio.validar_manual({"docente": "A, B", "dia": "lunes", "modulos": "1-14"})

    def test_dia_invalido(self):
        with self.assertRaises(ValueError):
            repositorio.validar_manual({"docente": "A, B", "dia": "sabado", "modulos": "1"})

    def test_turno_de(self):
        self.assertEqual(repositorio.turno_de("1-6"), "Mañana")
        self.assertEqual(repositorio.turno_de("8-9"), "Tarde")
        self.assertEqual(repositorio.turno_de("5-8"), "Mañana y tarde")

    def test_el_csv_guardado_lo_lee_horarios_manuales(self):
        import horarios_manuales
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "m.csv")
            repositorio.guardar_manuales(ruta, [{"docente": "A, B", "dia": "martes", "modulos": "1-4,8-9"}])
            docente = horarios_manuales.cargar(ruta)[0]
            self.assertEqual(len(docente.ocupadas), 6)


class FijarTratamiento(unittest.TestCase):
    def test_crea_y_actualiza(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "docentes.csv")
            maestro.fijar_tratamiento(ruta, "Perez, Ana", "Profesora")
            self.assertEqual(maestro.cargar_maestro(ruta)["perez ana"]["tratamiento"], "Profesora")
            maestro.fijar_tratamiento(ruta, "Perez, Ana", "Profesor")
            self.assertEqual(maestro.cargar_maestro(ruta)["perez ana"]["tratamiento"], "Profesor")

    def test_rechaza_otro_valor(self):
        with self.assertRaises(ValueError):
            maestro.fijar_tratamiento("x.csv", "Perez, Ana", "Doctor")


if __name__ == "__main__":
    unittest.main()


class Excluidos(unittest.TestCase):
    def test_guardar_conserva_otras_excepciones(self):
        import excepciones
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "excepciones.csv")
            excepciones.escribir([{"docente": "Otro, Uno", "dias": "lunes", "turno": "tm", "desde": "", "hasta": "2026-12-01",
                                   "motivo": "cubre"}], ruta)
            repositorio.guardar_excluidos(ruta, [{"docente": "Perez, Ana", "motivo": "ya no está"}])
            self.assertEqual(repositorio.leer_excluidos(ruta), [{"docente": "Perez, Ana", "motivo": "ya no está"}])
            vigentes, *_ = excepciones.cargar(ruta, date(2026, 10, 28))
            self.assertEqual({e["docente"] for e in vigentes}, {"Otro, Uno", "Perez, Ana"})
            repositorio.guardar_excluidos(ruta, [])
            self.assertEqual(len(excepciones.cargar(ruta, date(2026, 10, 28))[0]), 1)


class Nombres(unittest.TestCase):
    def test_inicial_y_nombre_compuesto(self):
        self.assertTrue(maestro.misma_persona("PEREZ LIMA, A.", "Perez Lima, Ma. Alejandra"))
        self.assertTrue(maestro.misma_persona("SOSA,  Cesar", "SOSA, Cesar Daniel"))
        self.assertFalse(maestro.misma_persona("SOSA, Cesar", "SOSA, Mario"))


class ExcluidosRepetidos(unittest.TestCase):
    def test_no_deja_agregar_dos_veces(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "excepciones.csv")
            with self.assertRaises(ValueError):
                repositorio.guardar_excluidos(ruta, [{"docente": "Perez, Ana", "motivo": ""},
                                                     {"docente": "PEREZ,  Ana", "motivo": ""}])
