"""Maestro de docentes: nombre impreso y tratamiento (Profesor/a) por docente.

`docentes.csv` está indexado por el nombre tal como lo escribe Untis (normalizado
con `clave_docente`). Se completa solo desde el export del .mdb
(`datos/mdb_tratamiento.csv`, ver `exportar_mdb.ps1`) y lo que no se pueda
resolver queda en blanco y detiene la generación: no se adivina el género.
"""
import csv
import difflib
import os
import re

from clasificar import clave_docente

TRATAMIENTOS = {"PROFESOR": "Profesor", "PROFESORA": "Profesora"}
HOJAS_LIBRO = ("prof. tm 2026", "prof.tmyt.2026")
CAMPOS = ["clave", "impreso", "tratamiento"]


def _partir(nombre):
    """('apellido', 'nombres') de 'Apellido, Nombres' o 'Apellido; Nombres'."""
    apellido, _, resto = re.sub(r";", ",", nombre).partition(",")
    return apellido.strip(), resto.strip()


def nombre_impreso(nombre):
    """'Garcia Lima; Ana' -> 'GARCIA LIMA, Ana' (formato del libro)."""
    apellido, resto = _partir(nombre)
    return f"{apellido.upper()}, {' '.join(resto.split())}"


def _tokens(texto):
    return set(clave_docente(texto.replace(".", " ")).split())


def cargar_mdb(ruta_csv):
    """[(apellido_tokens, nombre_tokens, tratamiento)] solo de PROFESOR/PROFESORA."""
    filas = []
    with open(ruta_csv, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            trat = TRATAMIENTOS.get(r["Cargo"].strip().upper())
            if trat:
                filas.append((_tokens(r["Apellidos"]), _tokens(r["Nombre"]), trat))
    return filas


def cargar_libro(ruta_xlsx):
    """[(apellido_tokens, nombre_tokens, tratamiento)] de los nombres ya impresos en las hojas actuales.

    Segunda fuente para quienes el .mdb no tiene o tiene con otro cargo. Se descartan los
    docentes que figuran con tratamientos distintos en el propio libro (inconsistentes).
    """
    import openpyxl

    vistos = {}
    wb = openpyxl.load_workbook(ruta_xlsx, read_only=True)
    for hoja in HOJAS_LIBRO:
        for fila in wb[hoja].iter_rows(min_row=2, values_only=True):
            for c0 in range(0, len(fila) - 2, 4):
                nombre, trat = fila[c0 + 1], fila[c0 + 2]
                if nombre and trat in TRATAMIENTOS.values():
                    vistos.setdefault(str(nombre), set()).add(trat)
    filas = []
    for nombre, tratamientos in vistos.items():
        if len(tratamientos) == 1:
            ap, nom = _partir(nombre)
            filas.append((_tokens(ap), _tokens(nom), next(iter(tratamientos))))
    return filas


def _mismo_apellido(a, b, umbral=0.9):
    if a == b or a <= b or b <= a:
        return True
    return difflib.SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio() >= umbral


def misma_persona(nombre_a, nombre_b):
    """True si dos escrituras ('Casal, Marlene' / 'CASAL, Marlen') parecen la misma persona."""
    (ap_a, no_a), (ap_b, no_b) = _partir(nombre_a), _partir(nombre_b)
    return _mismo_apellido(_tokens(ap_a), _tokens(ap_b), 0.8) and _nombre_compatible(_tokens(no_a), _tokens(no_b))


def _nombre_compatible(a, b):
    """Comparten un nombre, o uno es prefijo del otro; una inicial sola ("A.") encaja con el nombre que empieza así."""
    return bool(a & b) or any(x.startswith(y) or y.startswith(x) for x in a for y in b if min(len(x), len(y)) >= 1)


def buscar_tratamiento(nombre, fuente):
    """Tratamiento si todos los docentes de `fuente` que encajan con `nombre` coinciden; si no, ''."""
    apellido, resto = _partir(nombre)
    ap, nom = _tokens(apellido), _tokens(resto)
    candidatos = {t for a, n, t in fuente if _mismo_apellido(a, ap) and _nombre_compatible(n, nom)}
    return candidatos.pop() if len(candidatos) == 1 else ""


def cargar_maestro(ruta):
    if not os.path.exists(ruta):
        return {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return {r["clave"]: r for r in csv.DictReader(f)}


def guardar_maestro(maestro, ruta):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, CAMPOS)
        w.writeheader()
        for clave in sorted(maestro):
            w.writerow(maestro[clave])


def fijar_tratamiento(ruta_maestro, nombre, tratamiento):
    """Guarda el tratamiento que el usuario eligió para un docente (lo confirma una persona, no se adivina)."""
    if tratamiento not in ("Profesor", "Profesora"):
        raise ValueError(f"tratamiento inválido: {tratamiento!r}")
    maestro = cargar_maestro(ruta_maestro)
    clave = clave_docente(nombre)
    fila = maestro.setdefault(clave, {"clave": clave, "impreso": nombre_impreso(nombre), "tratamiento": ""})
    fila["tratamiento"] = tratamiento
    guardar_maestro(maestro, ruta_maestro)


def completar_maestro(nombres, ruta_maestro, ruta_mdb, ruta_libro=None):
    """Agrega los docentes que falten. Devuelve (maestro, sin_tratamiento, discrepancias).

    El .mdb manda; el libro actual completa lo que el .mdb no resuelve. Si ambos
    resuelven y difieren, se informa en `discrepancias` y se usa el del .mdb.
    """
    maestro = cargar_maestro(ruta_maestro)
    mdb = cargar_mdb(ruta_mdb) if os.path.exists(ruta_mdb) else []
    libro = cargar_libro(ruta_libro) if ruta_libro and os.path.exists(ruta_libro) else []
    discrepancias = []
    for nombre in nombres:
        clave = clave_docente(nombre)
        fila = maestro.get(clave)
        if fila is None:
            fila = maestro[clave] = {"clave": clave, "impreso": nombre_impreso(nombre), "tratamiento": ""}
        if not fila["tratamiento"]:
            en_mdb, en_libro = buscar_tratamiento(nombre, mdb), buscar_tratamiento(nombre, libro)
            fila["tratamiento"] = en_mdb or en_libro
            if en_mdb and en_libro and en_mdb != en_libro:
                discrepancias.append(f"{nombre}: .mdb dice {en_mdb}, el libro actual dice {en_libro}")
    guardar_maestro(maestro, ruta_maestro)
    sin = [n for n in nombres if not maestro[clave_docente(n)]["tratamiento"]]
    return maestro, sin, discrepancias
