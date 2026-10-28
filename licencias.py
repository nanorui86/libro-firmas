"""Licencias docentes: el docente sigue en la lista mientras dura la licencia.

`licencias.csv` (no se versiona) es además el registro de licencias:
    docente;desde;hasta;motivo;en_lista
    Apellido, Nombre;2026-09-01;2027-03-01;licencia por maternidad;si
Fechas ISO; `hasta` vacío = sin fecha de fin (el informe lo marca). `en_lista` es `si` (por defecto) o `no`.

- Vigente y `en_lista = si`: el docente figura en las mismas hojas y días de siempre, aunque el horario
  nuevo ya no lo traiga. Los turnos salen del último libro generado o, la primera vez, del libro actual.
- Vigente y `en_lista = no`: se lo saca de la lista.
- Vencida: ya no tiene efecto (si vuelve a tener clases en el horario, figura como cualquier docente).
- Futura: todavía no tiene efecto.
"""
import csv
import os
from datetime import date

from clasificar import clave_docente

CAMPOS = ["docente", "desde", "hasta", "motivo", "en_lista"]


def _fecha(texto):
    return date.fromisoformat(texto.strip()) if texto and texto.strip() else None


def cargar(ruta, hoy):
    """Devuelve {'vigentes', 'vencidas', 'futuras', 'sin_fin'}, cada una una lista de dicts."""
    grupos = {"vigentes": [], "vencidas": [], "futuras": [], "sin_fin": []}
    if not os.path.exists(ruta):
        return grupos
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for n, fila in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            en_lista = (fila.get("en_lista") or "si").strip().lower()
            if en_lista not in ("si", "no"):
                raise ValueError(f"licencias.csv, línea {n}: en_lista debe ser si o no ({en_lista!r})")
            desde, hasta = _fecha(fila["desde"]), _fecha(fila["hasta"])
            if desde and hasta and desde > hasta:
                raise ValueError(f"licencias.csv, línea {n}: 'desde' es posterior a 'hasta'")
            lic = dict(fila, clave=clave_docente(fila["docente"]), desde=desde, hasta=hasta, en_lista=en_lista == "si")
            if desde and desde > hoy:
                grupos["futuras"].append(lic)
            elif hasta and hasta < hoy:
                grupos["vencidas"].append(lic)
            else:
                grupos["vigentes"].append(lic)
                if not hasta:
                    grupos["sin_fin"].append(lic)
    return grupos


def aplicar(asignacion, vigentes, turnos_previos):
    """Ajusta {(clave, día): turno} según las licencias vigentes.

    `turnos_previos(nombre)` devuelve ({día: turno}, origen); vacío si no se sabe.
    Devuelve (notas para el informe, docentes de los que no se sabe en qué turnos estaban).
    """
    notas, sin_datos = [], []
    for lic in vigentes:
        clave, nombre = lic["clave"], lic["docente"]
        propios = [k for k in asignacion if k[0] == clave]
        if not lic["en_lista"]:
            for k in propios:
                del asignacion[k]
            notas.append(f"  {nombre}: NO figura en la lista (marcado en_lista = no)")
        elif propios:
            notas.append(f"  {nombre}: figura en la lista (todavía tiene clases en el horario)")
        else:
            dias, origen = turnos_previos(nombre)
            if not dias:
                sin_datos.append(nombre)
                continue
            for dia, turno in dias.items():
                asignacion[(clave, dia)] = turno
            notas.append(f"  {nombre}: figura en la lista con los turnos de siempre (según {origen})")
    return notas, sin_datos
