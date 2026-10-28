"""Convierte el texto de `informe.txt` en secciones legibles para la ventana (sin pantalla, con tests).

Cada sección: {'titulo', 'detalle' (el número o resumen que iba entre paréntesis o tras los dos puntos),
'ayuda' (la línea "Qué hacer"), 'tipo' ('lista' | 'cambios' | 'conteo' | 'error'), 'filas'}.
Una fila es un texto; en 'cambios' es (signo, hoja, día, nombre); en 'conteo', (hoja, [n por día]).
"""
import re

DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie"]
_CELDAS = re.compile(r"\s*\[(?:\(\d+, \d+\)(?:, )?)+\]")
_PAREN = re.compile(r"^(.*?)\s*\((\d+)([^)]*)\)\s*:?\s*$")


def _celdas_legibles(texto):
    """'... [(1, 3), (1, 4), (2, 5)]' -> '... (Mar mód. 3-4, Mié mód. 5)'."""
    def reemplazo(m):
        pares = re.findall(r"\((\d+), (\d+)\)", m.group(0))
        por_dia = {}
        for dia, mod in pares:
            por_dia.setdefault(int(dia), []).append(int(mod))
        partes = [f"{DIAS_CORTOS[d]} mód. {_tramos(sorted(mods))}" for d, mods in sorted(por_dia.items())]
        return " (" + ", ".join(partes) + ")"
    return _CELDAS.sub(reemplazo, texto)


def _tramos(mods):
    tramos, ini = [], mods[0]
    for ant, m in zip(mods, mods[1:] + [None]):
        if m is not None and m == ant + 1:
            continue
        tramos.append(str(ini) if ini == ant else f"{ini}-{ant}")
        ini = m
    return ", ".join(tramos)


def _titulo_y_detalle(linea):
    linea = linea.rstrip()
    m = _PAREN.match(linea)
    if m:
        return m.group(1).strip(), (m.group(2) + m.group(3)).strip()
    titulo, dos_puntos, resto = linea.partition(":")
    if dos_puntos and resto.strip() and not titulo.startswith("Generado"):
        return titulo.strip(), resto.strip()
    return linea.rstrip(":").strip(), ""


def parsear(texto):
    """Devuelve (encabezado: [líneas], secciones)."""
    bloques = [b for b in re.split(r"\n\s*\n", texto.strip("\n")) if b.strip()]
    encabezado, secciones = [], []
    for i, bloque in enumerate(bloques):
        lineas = bloque.split("\n")
        if i == 0:  # "Informe del ..." y "Docentes leídos ..."
            encabezado = [l.strip() for l in lineas]
            continue
        titulo, detalle = _titulo_y_detalle(lineas[0])
        if titulo.startswith("Generado"):
            titulo, detalle = lineas[0].strip(), ""
        sec = {"titulo": titulo, "detalle": detalle, "ayuda": "", "tipo": "lista", "filas": []}
        for linea in lineas[1:]:
            fila = linea.strip()
            if not fila:
                continue
            if fila.startswith("Qué hacer:"):
                sec["ayuda"] = fila[len("Qué hacer:"):].strip()
            else:
                sec["filas"].append(_celdas_legibles(linea.rstrip()).strip())
        if titulo.startswith("NO SE GENERÓ"):
            sec["tipo"] = "error"
        elif titulo.startswith("Cantidad de docentes"):
            sec["tipo"] = "conteo"
            sec["filas"] = [(f[:4].strip(), [int(n) for n in re.findall(r"\b(\d+)\b", f[4:])]) for f in sec["filas"]]
        elif titulo.startswith("Generado"):
            sec.update(tipo="pie", titulo="Libro generado", detalle="", filas=[titulo[len("Generado:"):].strip() or detalle])
        elif titulo.startswith("Qué cambia"):
            sec.update(tipo="cambios", titulo="Qué cambia respecto del libro actual", detalle="")
            cambios = []
            for f in sec["filas"]:
                m = re.match(r"([+-])\s+(tmyt|tm)\s+(\S+)\s+(.*)", f)
                if m:
                    cambios.append(m.groups())
            sec["filas"] = cambios
        secciones.append(sec)
    return encabezado, secciones
