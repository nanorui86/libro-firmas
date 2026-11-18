import os
import tempfile
import unittest
from datetime import date

import preceptores

HOY = date(2026, 11, 18)


def fila(apellido, nombre, cargo="Preceptor", dias="lunes,martes,miercoles,jueves,viernes", **lic):
    base = {"apellido": apellido, "nombre": nombre, "cargo": cargo, "dias": dias,
            "lic_desde": "", "lic_hasta": "", "lic_motivo": "", "en_lista": "si"}
    base.update(lic)
    return base


class Validar(unittest.TestCase):
    def test_normaliza_dias_y_en_lista(self):
        v = preceptores.validar(fila("Garcia", "Ana", dias="viernes, lunes", en_lista=""))
        self.assertEqual((v["dias"], v["en_lista"]), ("lunes,viernes", "si"))

    def test_exige_un_dia(self):
        with self.assertRaisesRegex(ValueError, "día"):
            preceptores.validar(fila("Garcia", "Ana", dias=""))

    def test_exige_apellido_y_nombre(self):
        with self.assertRaises(ValueError):
            preceptores.validar(fila("", "Ana"))
        with self.assertRaises(ValueError):
            preceptores.validar(fila("Garcia", " "))

    def test_rechaza_desde_posterior(self):
        with self.assertRaisesRegex(ValueError, "Desde"):
            preceptores.validar(fila("Garcia", "Ana", lic_desde="2026-12-01", lic_hasta="2026-11-01"))

    def test_fechas_dia_mes_anio(self):
        v = preceptores.validar(fila("Garcia", "Ana", lic_desde="01/11/2026", lic_hasta="30/11/2026"))
        self.assertEqual((v["lic_desde"], v["lic_hasta"]), ("2026-11-01", "2026-11-30"))

    def test_dia_desconocido(self):
        with self.assertRaises(ValueError):
            preceptores.validar(fila("Garcia", "Ana", dias="lunes,sabado"))


class Listas(unittest.TestCase):
    def test_ordena_sin_tildes_y_con_apostrofo(self):
        filas = [fila("Ríos de la Vega", "Maria", "Preceptora"), fila("Ñañez Lagos", "Lucía", "Preceptora"),
                 fila("D'Alba", "Carla", "Preceptora"), fila("Gomez", "Beto")]
        lunes = preceptores.listas_por_dia(filas, HOY)[0]
        self.assertEqual([n for n, _ in lunes], ["D'ALBA, Carla", "GOMEZ, Beto", "ÑAÑEZ LAGOS, Lucía",
                                                 "RÍOS DE LA VEGA, Maria"])
        self.assertEqual(lunes[0][1], "Preceptora")

    def test_solo_los_dias_tildados(self):
        filas = [fila("Garcia", "Ana", dias="lunes,martes"), fila("Perez", "Beto", dias="viernes")]
        listas = preceptores.listas_por_dia(filas, HOY)
        self.assertEqual([len(d) for d in listas], [1, 1, 0, 0, 1])

    def test_licencia_vigente_en_lista_si_sigue(self):
        f = fila("Garcia", "Ana", lic_desde="2026-11-01", lic_hasta="2026-11-30", lic_motivo="licencia")
        self.assertEqual(len(preceptores.listas_por_dia([f], HOY)[0]), 1)

    def test_licencia_vigente_en_lista_no_la_saca(self):
        f = fila("Garcia", "Ana", lic_desde="2026-11-01", lic_hasta="2026-11-30", lic_motivo="licencia", en_lista="no")
        self.assertEqual(len(preceptores.listas_por_dia([f], HOY)[0]), 0)

    def test_licencia_sin_fechas_con_en_lista_no_la_saca(self):
        f = fila("Garcia", "Ana", lic_motivo="licencia", en_lista="no")
        self.assertEqual(len(preceptores.listas_por_dia([f], HOY)[0]), 0)

    def test_vencida_o_futura_no_la_saca(self):
        vencida = fila("Garcia", "Ana", lic_desde="2026-09-01", lic_hasta="2026-10-31", en_lista="no")
        futura = fila("Perez", "Beto", lic_desde="2026-12-01", lic_hasta="2026-12-31", en_lista="no")
        self.assertEqual(len(preceptores.listas_por_dia([vencida, futura], HOY)[0]), 2)

    def test_estado(self):
        self.assertEqual(preceptores.estado(fila("Garcia", "Ana"), HOY), "")
        self.assertEqual(preceptores.estado(fila("Garcia", "Ana", lic_desde="2026-12-01"), HOY), "Todavía no empezó")
        self.assertEqual(preceptores.estado(fila("Garcia", "Ana", lic_hasta="2026-10-31"), HOY), "Vencida")
        self.assertEqual(preceptores.estado(fila("Garcia", "Ana", lic_motivo="licencia"), HOY), "Vigente, sin fecha de fin")

    def test_licencias_vigentes(self):
        filas = [fila("Garcia", "Ana", lic_hasta="2026-11-30"), fila("Perez", "Beto"),
                 fila("Gomez", "Carla", lic_hasta="2026-10-01")]
        self.assertEqual([preceptores.impreso(f) for f in preceptores.licencias_vigentes(filas, HOY)], ["GARCIA, Ana"])


class Archivo(unittest.TestCase):
    def test_leer_inexistente(self):
        self.assertEqual(preceptores.leer(os.path.join(tempfile.gettempdir(), "no_existe_prec.csv")), [])

    def test_guardar_y_leer(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "preceptores.csv")
            preceptores.guardar(ruta, [fila("Ñañez", "Lucía", dias="martes,lunes", lic_desde="01/11/2026")])
            leidas = preceptores.leer(ruta)
            self.assertEqual((leidas[0]["apellido"], leidas[0]["dias"], leidas[0]["lic_desde"]),
                             ("Ñañez", "lunes,martes", "2026-11-01"))

    def test_guardar_rechaza_repetidos(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "ya está"):
                preceptores.guardar(os.path.join(d, "p.csv"), [fila("Garcia", "Ana"), fila("GARCIA", "ana")])

    def test_guardar_no_escribe_si_hay_un_error(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "p.csv")
            with self.assertRaises(ValueError):
                preceptores.guardar(ruta, [fila("Garcia", "Ana"), fila("Perez", "Beto", dias="")])
            self.assertFalse(os.path.exists(ruta))


if __name__ == "__main__":
    unittest.main()
