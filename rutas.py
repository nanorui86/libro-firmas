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


def motivo(ruta):
    """Por qué no se puede abrir una carpeta, en palabras de Windows ('' si se puede)."""
    try:
        os.listdir(ruta)
        return ""
    except OSError as e:
        codigo = getattr(e, "winerror", None) or e.errno
        return f"{e.strerror or type(e).__name__} (código {codigo})"


def _resolver(ruta_config=RUTA_CONFIG_TXT):
    """(carpeta, aviso). El aviso queda vacío si todo está bien."""
    pedida = leer_config_txt(ruta_config).get("Datos", "")
    if not pedida:
        return LOCAL, ""
    por_que = motivo(pedida)
    if not por_que:
        return pedida, ""
    detalle = f"No se pudo abrir la carpeta de datos compartida:\n{pedida}\n\nMotivo: {por_que}\n\n"
    if os.path.isdir(LOCAL):
        return LOCAL, detalle + ("Se usa la copia local de este equipo, que puede estar desactualizada. Los cambios que hagas "
                                 "ahora NO se verán en las demás PC.")
    return pedida, detalle + "Sin esa carpeta el programa no tiene los datos."


def fijar_carpeta_datos(carpeta, ruta_config=RUTA_CONFIG_TXT):
    """Guarda `Datos=carpeta` en config.txt (conserva las demás líneas)."""
    lineas = []
    try:
        with open(ruta_config, encoding="utf-8-sig") as f:
            lineas = [l.rstrip("\r\n") for l in f if not l.strip().startswith("Datos=")]
    except OSError:
        lineas = ["# Configuración de Libro de firmas. Datos = carpeta compartida con los registros."]
    lineas.append(f"Datos={carpeta}")
    with open(ruta_config, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lineas) + "\n")


CARPETA_DATOS, AVISO = _resolver()


def en_datos(nombre):
    return os.path.join(CARPETA_DATOS, nombre)
