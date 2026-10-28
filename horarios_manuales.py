"""Horarios transcriptos a mano de PDFs que no se pueden leer por coordenadas (escaneos, fotos).

`horarios_manuales.csv` (no se versiona) tiene una fila por docente y día:
    docente;dia;modulos
    Apellido, Nombre;lunes;1-6
    Apellido, Nombre;miercoles;1-4,8-9
`modulos` son los módulos ocupados (1-13); un rango o una lista separada por comas. Las celdas de
"planificación" cuentan como presencia. Se transcribe una vez por horario y se revisa a ojo.
"""
import csv

from clasificar import DIAS, ULTIMO_MODULO
from parse_horario import Docente


def parsear_modulos(texto):
    modulos = set()
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        desde, _, hasta = parte.partition("-")
        modulos.update(range(int(desde), int(hasta or desde) + 1))
    if not modulos or any(not 1 <= m <= ULTIMO_MODULO for m in modulos):
        raise ValueError(f"módulos inválidos: {texto!r}")
    return modulos


def cargar(ruta):
    """Lista de Docente (uno por nombre) con la ocupación transcripta."""
    ocupacion = {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for n, fila in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            dia = fila["dia"].strip().lower()
            if dia not in DIAS:
                raise ValueError(f"{ruta}, línea {n}: día inválido {fila['dia']!r}")
            try:
                modulos = parsear_modulos(fila["modulos"])
            except ValueError as e:
                raise ValueError(f"{ruta}, línea {n}: {e}") from None
            ocupacion.setdefault(fila["docente"].strip(), set()).update((DIAS.index(dia), m) for m in modulos)
    return [
        Docente(nombre=nombre, horas="", ocupadas=celdas, avisos=["transcripto a mano de un PDF escaneado"])
        for nombre, celdas in ocupacion.items()
    ]
