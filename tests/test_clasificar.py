import unittest

from clasificar import clasificar, clave_docente


class TestClasificar(unittest.TestCase):
    def test_solo_manana(self):
        self.assertEqual(clasificar({1, 2, 3}), "tm")

    def test_limite_modulo_7_es_manana(self):
        self.assertEqual(clasificar({7}), "tm")

    def test_limite_modulo_8_es_tarde(self):
        self.assertEqual(clasificar({8}), "tmyt")

    def test_solo_tarde_va_en_tmyt(self):
        self.assertEqual(clasificar({9, 10, 13}), "tmyt")

    def test_mixto(self):
        self.assertEqual(clasificar({5, 6, 7, 8}), "tmyt")

    def test_sin_clases(self):
        self.assertIsNone(clasificar(set()))

    def test_modulo_invalido(self):
        with self.assertRaises(ValueError):
            clasificar({0})
        with self.assertRaises(ValueError):
            clasificar({14})


class TestClave(unittest.TestCase):
    def test_punto_y_coma(self):
        self.assertEqual(clave_docente("Lopez; Ana"), clave_docente("LOPEZ, Ana"))

    def test_doble_espacio_y_tildes(self):
        self.assertEqual(clave_docente("SOSA,  Lia"), "sosa lia")
        self.assertEqual(clave_docente("Ríos, Pedro"), clave_docente("RIOS, Pedro"))

    def test_enie_se_conserva_como_n(self):
        self.assertEqual(clave_docente("IBAÑEZ ROJAS, Nicolás"), "ibanez rojas nicolas")


if __name__ == "__main__":
    unittest.main()
