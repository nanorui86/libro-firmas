"""Genera las hojas del libro de firmas docente a partir del PDF de horarios de Untis.

    python libro_firmas.py "entrada/Profesores ....pdf" --cursos "entrada/Cursos ....pdf"

Escribe en salida/: el libro .xlsx, el CSV largo del horario y informe.txt.
Nunca modifica el libro original ni el molde.
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date

import pdfplumber

import excepciones
import horarios_manuales
import maestro
import parse_horario
import render_libro
import validar
from clasificar import DIAS, clasificar, clave_docente

NOMBRE_DIA = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")


def fecha_vigencia(ruta_pdf):
    with pdfplumber.open(ruta_pdf) as pdf:
        m = re.search(r"a partir del (\d{2})/(\d{2})/(\d{4})", pdf.pages[0].extract_text() or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def asignar(docentes):
    """{(clave, día 0-4): 'tm'|'tmyt'} según los módulos ocupados."""
    modulos = defaultdict(set)
    for d in docentes:
        for dia, mod in d.ocupadas:
            modulos[(clave_docente(d.nombre), dia)].add(mod)
    return {k: clasificar(m) for k, m in modulos.items()}


def armar_listas(asignacion, maes):
    """{turno: [por día: [(impreso, tratamiento)] ordenado]}"""
    listas = {t: [[] for _ in DIAS] for t in ("tm", "tmyt")}
    for (clave, dia), turno in asignacion.items():
        fila = maes[clave]
        listas[turno][dia].append((fila["impreso"], fila["tratamiento"]))
    for turno in listas:
        for dia in range(5):
            listas[turno][dia].sort(key=lambda x: clave_docente(x[0]))
    return listas


def _emparejar(previos, nuevos):
    """Empareja nombres que son la misma persona escrita distinto. Devuelve (solo_previos, solo_nuevos)."""
    libres = list(nuevos)
    solo_previos = []
    for p in previos:
        hit = next((n for n in libres if maestro.misma_persona(p, n)), None)
        if hit is None:
            solo_previos.append(p)
        else:
            libres.remove(hit)
    return solo_previos, libres


def diferencias(antes, listas):
    """Líneas con quién se agrega o sale por hoja y día respecto del libro actual."""
    lineas = []
    for turno in ("tm", "tmyt"):
        for dia in range(5):
            quitan, agregan = _emparejar(antes[turno][dia], [n for n, _ in listas[turno][dia]])
            lineas += [f"  + {turno:4} {NOMBRE_DIA[dia]:9} {n}" for n in sorted(agregan, key=clave_docente)]
            lineas += [f"  - {turno:4} {NOMBRE_DIA[dia]:9} {n}" for n in sorted(quitan, key=clave_docente)]
    return lineas


def ausentes_del_pdf(antes, nombres_pdf):
    """Docentes del libro actual que no aparecen en ninguna página del PDF."""
    en_libro = {n for turno in antes.values() for dia in turno for n in dia}
    return sorted(
        (n for n in en_libro if not any(maestro.misma_persona(n, p) for p in nombres_pdf)), key=clave_docente
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profesores", help="PDF de horarios por docente")
    ap.add_argument("--cursos", help="PDF de horarios por curso (validación cruzada)")
    ap.add_argument("--plantilla", default="datos/plantilla_libro.xlsx")
    ap.add_argument("--maestro", default="datos/docentes.csv")
    ap.add_argument("--mdb", default="datos/mdb_tratamiento.csv")
    ap.add_argument("--excepciones", default="datos/excepciones.csv")
    ap.add_argument("--manuales", default="datos/horarios_manuales.csv", help="horarios transcriptos a mano (escaneos)")
    ap.add_argument("--salida", default="salida")
    ap.add_argument("--fecha", help="fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    args = ap.parse_args(argv)

    hoy = date.fromisoformat(args.fecha) if args.fecha else date.today()
    os.makedirs(args.salida, exist_ok=True)
    informe = [f"Informe del {hoy.isoformat()} - horario: {os.path.basename(args.profesores)}"]
    detener = []

    docentes = parse_horario.leer_pdf(args.profesores)
    vigencia = fecha_vigencia(args.profesores)
    parse_horario.escribir_csv(docentes, os.path.join(args.salida, "horario_largo.csv"))
    informe.append(f"Docentes leídos: {len(docentes)} (horario vigente desde {vigencia or 'fecha desconocida'})")

    if args.cursos:
        errores, avisos = validar.validar(docentes, args.cursos)
        informe.append(f"\nValidación cruzada con cursos: {len(errores)} errores, {len(avisos)} avisos")
        informe += [f"  ERROR {e}" for e in errores] + [f"  aviso {a}" for a in avisos]
        detener += errores
        faltantes = validar.docentes_solo_en_cursos(docentes, args.cursos)
        if faltantes:
            informe.append("\nDocentes sin página en el PDF de profesores, reconstruidos desde el PDF de cursos:")
            for nombre, celdas in sorted(faltantes.items()):
                informe.append(f"  {nombre}: {len(celdas)} módulos (REVISAR: el export de Untis la/lo dejó afuera)")
                docentes.append(parse_horario.Docente(nombre=nombre, horas="", ocupadas=set(celdas),
                                                      avisos=["tomado del PDF de cursos"]))
    else:
        informe.append("\nValidación cruzada: NO se hizo (falta --cursos)")

    if os.path.exists(args.manuales):
        manuales = horarios_manuales.cargar(args.manuales)
        repetidos = [m.nombre for m in manuales if any(maestro.misma_persona(m.nombre, d.nombre) for d in docentes)]
        detener += [f"{n}: figura en el PDF y en {args.manuales}; dejarlo en un solo lugar" for n in repetidos]
        informe.append(f"\nHorarios transcriptos a mano ({len(manuales)} docentes, de un PDF escaneado; revisar contra el original):")
        informe += [f"  {m.nombre}: {len(m.ocupadas)} módulos" for m in manuales]
        docentes += manuales

    vigentes, vencidas, futuras, sin_fin = excepciones.cargar(args.excepciones, hoy)
    nombres = [d.nombre for d in docentes] + [e["docente"] for e in vigentes]
    maes, sin_trat, discrepancias = maestro.completar_maestro(
        list(dict.fromkeys(nombres)), args.maestro, args.mdb, args.plantilla
    )
    asignacion = excepciones.aplicar(asignar(docentes), vigentes)
    en_libro = {clave for clave, _ in asignacion}
    sin_trat = [n for n in sin_trat if clave_docente(n) in en_libro]  # a quien no va en el libro no se le exige
    if sin_trat:
        detener.append(f"falta el tratamiento (Profesor/Profesora) de: {', '.join(sin_trat)} - completarlo en {args.maestro}")
    if discrepancias:
        informe.append("\nDiscrepancias de tratamiento (se usó el .mdb):")
        informe += [f"  {d}" for d in discrepancias]

    informe.append(f"\nExcepciones: {len(vigentes)} vigentes, {len(vencidas)} vencidas, {len(futuras)} futuras")
    informe += [
        f"  vigente: {e['docente']} {e['turno']} {','.join(e['dias'])} | {e['motivo']} | "
        f"desde {e['desde'] or '?'} hasta {e['hasta'] or 'sin fecha de fin'}"
        for e in vigentes
    ]
    informe += [f"  SIN FECHA DE FIN: {e['docente']} {e['turno']}" for e in sin_fin]
    informe += [f"  VENCIDA (no se aplicó): {e['docente']} hasta {e['hasta']}" for e in vencidas]

    sin_horas = [d.nombre for d in docentes if not d.ocupadas
                 and not any(clave_docente(d.nombre) == e["clave"] for e in vigentes)]
    if sin_horas:
        informe.append("\nDocentes en el PDF sin ninguna clase y sin excepción (no figuran en el libro):")
        informe += [f"  {n}" for n in sin_horas]

    listas = armar_listas(asignacion, maes)
    informe.append("\nCantidad de docentes por hoja y día:")
    for turno in ("tm", "tmyt"):
        informe.append(f"  {turno:4} " + "  ".join(f"{NOMBRE_DIA[i][:3]} {len(listas[turno][i]):2}" for i in range(5)))

    if os.path.exists(args.plantilla):
        antes = render_libro.leer_listas(args.plantilla)
        ausentes = [n for n in ausentes_del_pdf(antes, [d.nombre for d in docentes])
                    if not any(maestro.misma_persona(n, e["docente"]) for e in vigentes)]  # los explicados ya figuran arriba
        informe.append(f"\nEstán en el libro actual y NO en el PDF de horarios ({len(ausentes)}):")
        informe += [f"  {n}" for n in ausentes] or ["  ninguno"]
        informe.append("\nDiferencias contra el libro actual, con los nombres parecidos ya emparejados (+ se agrega, - sale):")
        informe += diferencias(antes, listas) or ["  ninguna"]

    ruta_informe = os.path.join(args.salida, "informe.txt")
    if detener:
        informe.append("\nNO SE GENERÓ EL LIBRO:")
        informe += [f"  {d}" for d in detener]
        open(ruta_informe, "w", encoding="utf-8").write("\n".join(informe) + "\n")
        print("\n".join(informe))
        return 1

    nombre = f"Lib. Firmas 2026 (horario {vigencia or hoy.isoformat()}).xlsx"
    render_libro.render(args.plantilla, os.path.join(args.salida, nombre), listas)
    informe.append(f"\nGenerado: {os.path.join(args.salida, nombre)}")
    open(ruta_informe, "w", encoding="utf-8").write("\n".join(informe) + "\n")
    print("\n".join(informe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
