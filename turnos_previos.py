"""Recuerda en qué hoja y día figuraba cada docente en el último libro generado.

Lo necesita `licencias.py`: un docente de licencia puede desaparecer del horario nuevo, y hay que saber
en qué turnos estaba para que siga en la lista. La memoria es `turnos_ultimo_libro.csv` (no se versiona),
que se reescribe cada vez que se genera un libro. La primera vez se usa el libro actual (la plantilla).
"""
import csv
import os

import maestro
from clasificar import DIAS

CAMPOS = ["docente", "dia", "turno"]


def desde_listas(listas):
    """{nombre: {día: turno}} de {turno: [por día: [nombre o (nombre, tratamiento)]]}."""
    previos = {}
    for turno, por_dia in listas.items():
        for dia, nombres in enumerate(por_dia):
            for n in nombres:
                nombre = n[0] if isinstance(n, tuple) else n
                previos.setdefault(nombre, {})[dia] = turno
    return previos


def guardar(listas, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(CAMPOS)
        for nombre, dias in sorted(desde_listas(listas).items()):
            for dia, turno in sorted(dias.items()):
                w.writerow([nombre, DIAS[dia], turno])


def cargar(ruta):
    previos = {}
    if os.path.exists(ruta):
        with open(ruta, newline="", encoding="utf-8-sig") as f:
            for fila in csv.DictReader(f, delimiter=";"):
                previos.setdefault(fila["docente"], {})[DIAS.index(fila["dia"])] = fila["turno"]
    return previos


def buscar(nombre, *fuentes):
    """({día: turno}, origen) de la primera fuente (origen, previos) donde aparece esa persona."""
    for origen, previos in fuentes:
        for otro, dias in previos.items():
            if maestro.misma_persona(nombre, otro):
                return dias, origen
    return {}, ""
