import os
import tempfile
import unittest

import rutas


class ConfigTxt(unittest.TestCase):
    def test_lee_clave_valor_e_ignora_comentarios(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "config.txt")
            with open(ruta, "w", encoding="utf-8-sig") as f:
                f.write("# comentario\nDatos=\\servidor\carpeta con tilde í\n\nOtra = x = y\n")
            self.assertEqual(rutas.leer_config_txt(ruta), {"Datos": "\\servidor\carpeta con tilde í", "Otra": "x = y"})

    def test_sin_archivo(self):
        self.assertEqual(rutas.leer_config_txt(os.path.join(tempfile.gettempdir(), "no_existe_cfg.txt")), {})


class Resolver(unittest.TestCase):
    def _cfg(self, d, datos):
        ruta = os.path.join(d, "config.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"Datos={datos}\n")
        return ruta

    def test_sin_config_usa_la_carpeta_local(self):
        carpeta, aviso = rutas._resolver(os.path.join(tempfile.gettempdir(), "no_existe_cfg.txt"))
        self.assertEqual((carpeta, aviso), (rutas.LOCAL, ""))

    def test_carpeta_compartida_accesible(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(rutas._resolver(self._cfg(d, d)), (d, ""))

    def test_carpeta_inaccesible_avisa(self):
        with tempfile.TemporaryDirectory() as d:
            carpeta, aviso = rutas._resolver(self._cfg(d, os.path.join(d, "no_hay")))
            self.assertIn("No se pudo abrir la carpeta de datos compartida", aviso)
            if os.path.isdir(rutas.LOCAL):
                self.assertEqual(carpeta, rutas.LOCAL)


if __name__ == "__main__":
    unittest.main()
