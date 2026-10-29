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


class Motivo(unittest.TestCase):
    def test_carpeta_que_existe_no_tiene_motivo(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(rutas.motivo(d), "")

    def test_carpeta_que_no_existe_da_el_motivo(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("código", rutas.motivo(os.path.join(d, "no_hay")))

    def test_fijar_carpeta_conserva_otras_lineas(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "config.txt")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("Otra=1\nDatos=" + r"\\viejo\carpeta" + "\n")
            nueva = r"Z:\datos con tilde í"
            rutas.fijar_carpeta_datos(nueva, ruta)
            self.assertEqual(rutas.leer_config_txt(ruta), {"Otra": "1", "Datos": nueva})


class BarraPerdida(unittest.TestCase):
    """Un config.txt con la ruta de red escrita con una sola barra inicial se interpreta como ruta de red."""

    def test_corrige_una_sola_barra(self):
        self.assertEqual(rutas.corregir_barra(r"\Servidor\carpeta"), r"\\Servidor\carpeta")

    def test_no_toca_las_rutas_bien_escritas(self):
        for ok in (r"\\Servidor\carpeta", r"C:\datos", r"Z:\carpeta con espacios"):
            self.assertEqual(rutas.corregir_barra(ok), ok)

    def test_resolver_repara_el_config(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "config.txt")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("Datos=" + os.path.join(d, "x") + "\n")  # ruta de unidad: no se toca
            self.assertEqual(rutas._resolver(ruta)[0], os.path.join(d, "x")) if os.path.isdir(os.path.join(d, "x")) else None
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("Datos=" + "\\" + "Servidor_inexistente" + "\\datos\n")
            carpeta, aviso = rutas._resolver(ruta)
            self.assertIn("\\\\Servidor_inexistente", aviso)  # el aviso ya muestra la ruta corregida
