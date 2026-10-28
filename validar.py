"""Controles cruzados contra errores silenciosos del parser.

1. Cruce con el PDF de cursos: cada celda curso/día/módulo nombra a su docente;
   debe coincidir con la ocupación leída del PDF de profesores.
2. Horas declaradas en la cabecera vs módulos ocupados (aviso, no error).
3. Páginas = docentes distintos y sin nombres vacíos.
"""
import sys
from collections import defaultdict

import pdfplumber

from clasificar import clave_docente

# Bordes de la grilla del PDF de cursos (verificados en el del 23/10/2026).
BORDES_X = (102.3, 192.9, 282.9, 372.8, 462.8, 552.1)
BORDES_Y = tuple(99.4 + 51.8 * k for k in range(14))


def _celda(x, y):
    dia = next((i for i in range(5) if BORDES_X[i] <= x < BORDES_X[i + 1]), None)
    mod = next((i for i in range(13) if BORDES_Y[i] <= y < BORDES_Y[i + 1]), None)
    return None if dia is None or mod is None else (dia, mod + 1)


def texto_por_celda(ruta_cursos):
    """{(curso, dia, modulo): set(palabras normalizadas)} del PDF de cursos."""
    celdas = defaultdict(set)
    with pdfplumber.open(ruta_cursos) as pdf:
        for pagina in pdf.pages:
            curso = pagina.page_number
            for w in pagina.extract_words():
                if w["top"] < BORDES_Y[0]:
                    continue
                c = _celda((w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2)
                if c:
                    celdas[(curso, *c)].update(clave_docente(w["text"]).split())
    return celdas


def ocupacion_por_cursos(docentes, ruta_cursos):
    """{nombre docente: set((dia, modulo))} según el PDF de cursos."""
    tokens = {d.nombre: set(clave_docente(d.nombre).split()) for d in docentes}
    ocupacion = defaultdict(set)
    for (_, dia, mod), palabras in texto_por_celda(ruta_cursos).items():
        for nombre, t in tokens.items():
            if t and t <= palabras:
                ocupacion[nombre].add((dia, mod))
    return ocupacion


TAM_DOCENTE_EN_CURSOS = 6.3  # los nombres de docentes son lo único con este tamaño de fuente


def docentes_solo_en_cursos(docentes, ruta_cursos):
    """{nombre: set((dia, modulo))} de docentes que el PDF de cursos nombra y que no tienen
    página en el PDF de profesores (el export de Untis a veces deja a alguno afuera).

    Un nombre pegado a la celda puede venir cortado ('Alejan'): un token que es prefijo de
    uno conocido no cuenta como docente nuevo.
    """
    conocidas = {t for d in docentes for t in clave_docente(d.nombre).split()}

    def desconocida(t):
        return not any(k.startswith(t) for k in conocidas)

    encontrados = defaultdict(set)
    with pdfplumber.open(ruta_cursos) as pdf:
        for pagina in pdf.pages:
            lineas = defaultdict(list)
            for w in pagina.extract_words(extra_attrs=["size"]):
                if abs(w["size"] - TAM_DOCENTE_EN_CURSOS) < 0.2 and w["top"] >= BORDES_Y[0]:
                    if all(desconocida(t) for t in clave_docente(w["text"]).split()):
                        lineas[round(w["top"])].append(w)
            for palabras in lineas.values():
                palabras.sort(key=lambda w: w["x0"])
                grupo = [palabras[0]]
                for w in palabras[1:] + [None]:
                    if w is not None and w["x0"] - grupo[-1]["x1"] < 6:
                        grupo.append(w)
                        continue
                    nombre = " ".join(g["text"] for g in grupo)
                    cx = (grupo[0]["x0"] + grupo[-1]["x1"]) / 2
                    cy = (grupo[0]["top"] + grupo[0]["bottom"]) / 2
                    celda = _celda(cx, cy)
                    if celda:
                        encontrados[nombre].add(celda)
                    grupo = [w] if w is not None else []
    return dict(encontrados)


def validar(docentes, ruta_cursos):
    """Devuelve (errores, avisos) como listas de texto legibles."""
    errores, avisos = [], []
    nombres = [d.nombre for d in docentes]
    if any(not n for n in nombres):
        errores.append("hay páginas sin nombre de docente")
    repetidos = {n for n in nombres if nombres.count(n) > 1}
    if repetidos:
        errores.append(f"docentes en más de una página: {sorted(repetidos)}")

    por_cursos = ocupacion_por_cursos(docentes, ruta_cursos)
    for d in docentes:
        solo_prof = d.ocupadas - por_cursos.get(d.nombre, set())
        solo_cursos = por_cursos.get(d.nombre, set()) - d.ocupadas
        if solo_cursos:
            errores.append(f"{d.nombre}: figura en cursos y no en su horario {sorted(solo_cursos)}")
        if solo_prof:
            avisos.append(f"{d.nombre}: {len(solo_prof)} celda(s) sin curso asociado {sorted(solo_prof)}")
        try:
            declaradas = float(d.horas)
        except ValueError:
            errores.append(f"{d.nombre}: horas ilegibles ({d.horas!r})")
            continue
        if abs(declaradas - len(d.ocupadas)) > 0.01:
            avisos.append(f"{d.nombre}: {d.horas} h declaradas, {len(d.ocupadas)} módulos")
        for a in d.avisos:
            avisos.append(f"{d.nombre}: {a}")
    return errores, avisos


if __name__ == "__main__":
    from parse_horario import leer_pdf

    docs = leer_pdf(sys.argv[1])
    errores, avisos = validar(docs, sys.argv[2])
    print(f"{len(errores)} errores, {len(avisos)} avisos")
    for e in errores:
        print("ERROR", e)
    for a in avisos:
        print("aviso", a)
