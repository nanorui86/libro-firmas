"""Lee el PDF de horarios por docente exportado de Untis.

Una página por docente: cabecera con el nombre y una grilla Lunes-Viernes x 13
módulos. Una celda está ocupada si tiene texto o un rectángulo blanco propio
(Untis dibuja uno por celda con clase, sin fusionar dobles horas). Si las dos
señales no coinciden se registra en `avisos` en lugar de elegir una en silencio.
"""
import csv
import re
import sys
from dataclasses import dataclass, field

import pdfplumber

from clasificar import DIAS

# Bordes de la grilla en puntos (verificados en el PDF del 23/10/2026).
BORDES_X = (85.7, 179.2, 272.8, 366.3, 459.9, 552.8)
BORDES_Y = tuple(100.1 + 51.8 * k for k in range(14))
TOLERANCIA = 3.0
RE_HORAS = re.compile(r"(\d+\.\d+)")
TAM_NOMBRE, TAM_HORAS = 13.5, 18.0


@dataclass
class Docente:
    nombre: str
    horas: str
    ocupadas: set = field(default_factory=set)  # {(dia 0-4, modulo 1-13)}
    avisos: list = field(default_factory=list)
    pagina: int = 0


def nombre_y_horas(chars):
    """(nombre, horas) de los caracteres de la cabecera, separados por tamaño de fuente.

    El nombre va en Arial 13.5, el contacto (Casa/Celular) en negrita 10.8 y las horas
    en Arial 18. Separar por fuente evita que el celular se pegue a las horas
    ('15-3825219712.00 Horas') o se superponga con el nombre.
    """
    def texto(tam):
        sel = sorted((c for c in chars if abs(c["size"] - tam) < 0.3), key=lambda c: c["x0"])
        return "".join(c["text"] for c in sel)

    nombre = " ".join(texto(TAM_NOMBRE).split())
    m = RE_HORAS.search(texto(TAM_HORAS))
    return nombre, (m.group(1) if m else "")


def _celda(x, y):
    """(dia, modulo) para un punto, o None si cae fuera de la grilla."""
    dia = next((i for i in range(5) if BORDES_X[i] <= x < BORDES_X[i + 1]), None)
    mod = next((i for i in range(13) if BORDES_Y[i] <= y < BORDES_Y[i + 1]), None)
    if dia is None or mod is None:
        return None
    return dia, mod + 1


def _verificar_grilla(pagina):
    xs = sorted({round(l["x0"], 1) for l in pagina.lines if abs(l["x0"] - l["x1"]) < 0.5})
    for borde in BORDES_X:
        if not any(abs(borde - x) <= TOLERANCIA for x in xs):
            raise ValueError(
                f"página {pagina.page_number}: la grilla no coincide con el formato esperado "
                f"(falta borde x≈{borde}); el PDF cambió de diseño"
            )


def leer_pagina(pagina):
    _verificar_grilla(pagina)
    palabras = pagina.extract_words()

    nombre, horas = nombre_y_horas([c for c in pagina.chars if 47 <= c["top"] <= 62])
    doc = Docente(nombre=nombre, horas=horas, pagina=pagina.page_number)
    if not nombre:
        doc.avisos.append("nombre vacío")

    por_texto, por_rect = set(), set()
    for w in palabras:
        if w["top"] >= BORDES_Y[0]:
            c = _celda((w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2)
            if c:
                por_texto.add(c)
    for r in pagina.rects:
        color = r.get("non_stroking_color")
        if color and tuple(color) == (1.0, 1.0, 1.0) and r["top"] >= BORDES_Y[0]:
            ancho, alto = r["x1"] - r["x0"], r["bottom"] - r["top"]
            if ancho < 150 and alto < 80:  # descarta el fondo de toda la grilla
                c = _celda((r["x0"] + r["x1"]) / 2, (r["top"] + r["bottom"]) / 2)
                if c:
                    por_rect.add(c)

    doc.ocupadas = por_texto | por_rect
    for c in sorted(por_texto ^ por_rect):
        fuente = "solo texto" if c in por_texto else "solo rectángulo"
        doc.avisos.append(f"{DIAS[c[0]]} módulo {c[1]}: {fuente}")
    return doc


def leer_pdf(ruta):
    with pdfplumber.open(ruta) as pdf:
        return [leer_pagina(p) for p in pdf.pages]


def escribir_csv(docentes, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["docente", "dia", "modulo"])
        for d in docentes:
            for dia, mod in sorted(d.ocupadas):
                w.writerow([d.nombre, DIAS[dia], mod])


if __name__ == "__main__":
    docentes = leer_pdf(sys.argv[1])
    escribir_csv(docentes, sys.argv[2] if len(sys.argv) > 2 else "datos/horario_largo.csv")
    print(f"{len(docentes)} docentes leídos")
