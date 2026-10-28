"""Excepciones manuales al horario: licencias, suplentes, cargos que Untis no carga.

`excepciones.csv` (no se versiona) tiene una fila por docente y turno:
    docente;dias;turno;desde;hasta;motivo
    Apellido, Nombre;lunes,martes;tm;2026-10-16;2026-11-30;licencia, cubre X
`turno` es tm, tmyt o quitar. Fechas ISO; `hasta` vacío = sin fecha de fin (el
informe lo marca). Una excepción vencida no se aplica y el informe lo avisa.
"""
import csv
import os
from datetime import date

from clasificar import DIAS, clave_docente

CAMPOS = ["docente", "dias", "turno", "desde", "hasta", "motivo"]
TURNOS = ("tm", "tmyt", "quitar")


def _fecha(texto):
    return date.fromisoformat(texto.strip()) if texto and texto.strip() else None


def cargar(ruta, hoy):
    """Devuelve (vigentes, vencidas, futuras, sin_fin). Cada una es una lista de dicts."""
    vigentes, vencidas, futuras, sin_fin = [], [], [], []
    if not os.path.exists(ruta):
        return vigentes, vencidas, futuras, sin_fin
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for n, fila in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            turno = fila["turno"].strip()
            dias = [d.strip().lower() for d in fila["dias"].split(",") if d.strip()]
            if turno not in TURNOS or not dias or any(d not in DIAS for d in dias):
                raise ValueError(f"excepciones.csv, línea {n}: turno o días inválidos ({fila})")
            fila = dict(fila, clave=clave_docente(fila["docente"]), dias=dias,
                        desde=_fecha(fila["desde"]), hasta=_fecha(fila["hasta"]), turno=turno)
            if fila["desde"] and fila["desde"] > hoy:
                futuras.append(fila)
            elif fila["hasta"] and fila["hasta"] < hoy:
                vencidas.append(fila)
            else:
                vigentes.append(fila)
                if not fila["hasta"] and fila["turno"] != "quitar":  # quitar sin fin = exclusión permanente
                    sin_fin.append(fila)
    return vigentes, vencidas, futuras, sin_fin


def aplicar(asignacion, vigentes):
    """Modifica {(clave, dia): turno} según las excepciones vigentes."""
    for e in vigentes:
        for dia in e["dias"]:
            if e["turno"] == "quitar":
                asignacion.pop((e["clave"], DIAS.index(dia)), None)
            else:
                asignacion[(e["clave"], DIAS.index(dia))] = e["turno"]
    return asignacion


def escribir(filas, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, CAMPOS, delimiter=";")
        w.writeheader()
        w.writerows(filas)
