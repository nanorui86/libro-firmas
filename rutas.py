"""Dónde están los datos del programa.

Por defecto, en la carpeta `datos\` junto al programa. Si junto al programa hay un `config.txt` con una línea
`Datos=\\servidor\carpeta`, los datos (docentes, licencias, excluidos, plantilla...) se leen y se guardan ahí, así que
todas las PC que apunten a esa carpeta ven los mismos cambios. Si la carpeta compartida no responde (sin red), se usa
la copia local de `datos\` si existe y `AVISO` explica qué pasó.
"""
import os
import sys

BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG_TXT = os.path.join(BASE, "config.txt")
LOCAL = os.path.join(BASE, "datos")
AVISO = ""


def leer_config_txt(ruta=RUTA_CONFIG_TXT):
    """{clave: valor} de las líneas `clave=valor`; se ignoran las vacías y las que empiezan con #."""
    config = {}
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, _, valor = linea.partition("=")
                    config[clave.strip()] = valor.strip()
    except OSError:
        pass
    return config


def _resolver(ruta_config=RUTA_CONFIG_TXT):
    """(carpeta, aviso). El aviso queda vacío si todo está bien."""
    pedida = leer_config_txt(ruta_config).get("Datos", "")
    if not pedida:
        return LOCAL, ""
    if os.path.isdir(pedida):
        return pedida, ""
    if os.path.isdir(LOCAL):
        return LOCAL, (f"No se pudo abrir la carpeta de datos compartida:\n{pedida}\n\nSe usa la copia local de este equipo, "
                       "que puede estar desactualizada. Los cambios que hagas ahora NO se verán en las demás PC. "
                       "Revisá la conexión a la red y volvé a abrir el programa.")
    return pedida, (f"No se pudo abrir la carpeta de datos compartida:\n{pedida}\n\nRevisá la conexión a la red y volvé a abrir "
                    "el programa.")


CARPETA_DATOS, AVISO = _resolver()


def en_datos(nombre):
    return os.path.join(CARPETA_DATOS, nombre)
