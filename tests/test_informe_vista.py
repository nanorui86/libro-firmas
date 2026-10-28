import unittest

import informe_vista

TEXTO = """Informe del 2026-10-28 - horario: Prof.pdf
Docentes leídos: 3 (horario vigente desde 2026-10-16)

Control contra el horario de cursos: 0 errores, 2 avisos
  Qué hacer: nada.
  aviso Perez, Ana: 4 celda(s) sin curso asociado [(1, 3), (1, 4), (2, 5)]

Están en el libro actual y NO en el horario nuevo (0):
  ninguno

Cantidad de docentes por hoja y día:
  tm   Lun 25  Mar 22  Mié 19  Jue 20  Vie 30
  tmyt Lun 29  Mar 24  Mié 35  Jue 29  Vie 17

Qué cambia respecto del libro actual (+ entra en esa hoja y día, - sale):
  + tm   Lunes     PEREZ, Ana
  - tmyt Miércoles GOMEZ, Beto
"""


class Parser(unittest.TestCase):
    def setUp(self):
        self.enc, self.sec = informe_vista.parsear(TEXTO)

    def test_encabezado(self):
        self.assertEqual(len(self.enc), 2)

    def test_titulo_detalle_y_ayuda(self):
        s = self.sec[0]
        self.assertEqual((s["titulo"], s["detalle"], s["ayuda"]), ("Control contra el horario de cursos", "0 errores, 2 avisos", "nada."))

    def test_celdas_legibles(self):
        self.assertIn("(Mar mód. 3-4, Mié mód. 5)", self.sec[0]["filas"][0])
        self.assertNotIn("[(", self.sec[0]["filas"][0])

    def test_numero_entre_parentesis_pasa_a_detalle(self):
        self.assertEqual((self.sec[1]["titulo"], self.sec[1]["detalle"]), ("Están en el libro actual y NO en el horario nuevo", "0"))

    def test_conteo_y_cambios(self):
        self.assertEqual(self.sec[2]["filas"][0], ("tm", [25, 22, 19, 20, 30]))
        self.assertEqual(self.sec[3]["filas"], [("+", "tm", "Lunes", "PEREZ, Ana"), ("-", "tmyt", "Miércoles", "GOMEZ, Beto")])


if __name__ == "__main__":
    unittest.main()
