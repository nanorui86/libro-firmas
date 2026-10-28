"""Regla de turno del libro de firmas.

Módulos 1-7 (8:00-13:05) son turno mañana; 8-13 (13:45-18:05) son turno tarde.
Un día con algún módulo 8-13 va en la hoja 'tmyt' (mañana y tarde), aunque no
tenga nada a la mañana. Si solo tiene módulos 1-7, va en 'tm'.
"""
import re
import unicodedata

ULTIMO_MODULO_MANANA = 7
ULTIMO_MODULO = 13
DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes")


def clasificar(modulos):
    """Devuelve 'tmyt', 'tm' o None según los módulos ocupados ese día."""
    modulos = set(modulos)
    fuera = [m for m in modulos if not 1 <= m <= ULTIMO_MODULO]
    if fuera:
        raise ValueError(f"módulos fuera de rango 1-{ULTIMO_MODULO}: {sorted(fuera)}")
    if any(m > ULTIMO_MODULO_MANANA for m in modulos):
        return "tmyt"
    if modulos:
        return "tm"
    return None


def clave_docente(nombre):
    """Clave para cruzar fuentes: sin tildes, minúsculas, sin ';' ni espacios dobles."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn"
    )
    limpio = re.sub(r"[;,]", " ", sin_tildes.lower())
    return " ".join(limpio.split())
