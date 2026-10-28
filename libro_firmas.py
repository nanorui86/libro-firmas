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
from dataclasses import dataclass, field
from datetime import date

import pdfplumber

import excepciones
import horarios_manuales
import licencias
import maestro
import parse_horario
import render_libro
import turnos_previos
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


@dataclass
class Resultado:
    ok: bool
    informe: str
    ruta_libro: str = ""
    sin_tratamiento: list = field(default_factory=list)  # docentes a los que falta Profesor/Profesora
    problemas: list = field(default_factory=list)        # motivos por los que no se generó el libro
    conteo: dict = field(default_factory=dict)           # {'tm': [n por día], 'tmyt': [...]}
    avisos: list = field(default_factory=list)           # [(nivel, texto)]: 'aviso' o 'info'


def crear_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profesores", help="PDF de horarios por docente")
    ap.add_argument("--cursos", help="PDF de horarios por curso (validación cruzada)")
    ap.add_argument("--plantilla", default="datos/plantilla_libro.xlsx")
    ap.add_argument("--maestro", default="datos/docentes.csv")
    ap.add_argument("--mdb", default="datos/mdb_tratamiento.csv")
    ap.add_argument("--excepciones", default="datos/excepciones.csv")
    ap.add_argument("--manuales", default="datos/horarios_manuales.csv", help="horarios transcriptos a mano (escaneos)")
    ap.add_argument("--licencias", default="datos/licencias.csv", help="registro de licencias (desde, hasta, motivo)")
    ap.add_argument("--turnos-previos", default="datos/turnos_ultimo_libro.csv", help="memoria del último libro generado")
    ap.add_argument("--salida", default="salida")
    ap.add_argument("--fecha", help="fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    return ap


def opciones(profesores, base=None, **cambios):
    """Opciones de `generar` con los valores por defecto; las rutas relativas cuelgan de `base`."""
    args = crear_parser().parse_args([profesores])
    for nombre, valor in cambios.items():
        setattr(args, nombre, valor)
    if base:
        for nombre in ("plantilla", "maestro", "mdb", "excepciones", "manuales", "licencias", "turnos_previos", "salida"):
            ruta = getattr(args, nombre)
            if ruta and not os.path.isabs(ruta):
                setattr(args, nombre, os.path.join(base, ruta))
    return args


def main(argv=None):
    resultado = generar(crear_parser().parse_args(argv))
    print(resultado.informe)
    return 0 if resultado.ok else 1


def generar(args):
    """Arma el libro. `args` tiene los campos de `crear_parser`; devuelve un `Resultado`."""
    hoy = date.fromisoformat(args.fecha) if args.fecha else date.today()
    os.makedirs(args.salida, exist_ok=True)
    informe = [f"Informe del {hoy.isoformat()} - horario: {os.path.basename(args.profesores)}"]
    detener = []
    avisos_app = []  # (nivel, texto) para la ventana: lo que hay que mirar antes de imprimir

    docentes = parse_horario.leer_pdf(args.profesores)
    vigencia = fecha_vigencia(args.profesores)
    parse_horario.escribir_csv(docentes, os.path.join(args.salida, "horario_largo.csv"))
    informe.append(f"Docentes leídos: {len(docentes)} (horario vigente desde {vigencia or 'fecha desconocida'})")

    if args.cursos:
        errores, avisos = validar.validar(docentes, args.cursos)
        informe.append(f"\nControl contra el horario de cursos: {len(errores)} errores, {len(avisos)} avisos")
        informe.append("  Qué hacer: nada, salvo que haya ERROR. Los avisos son diferencias entre los dos PDF de Untis "
                       "(horas declaradas vs. módulos, celdas sin curso) y no cambian el libro.")
        informe += [f"  ERROR {e}" for e in errores] + [f"  aviso {a}" for a in avisos]
        detener += errores
        faltantes = validar.docentes_solo_en_cursos(docentes, args.cursos)
        if faltantes:
            informe.append("\nDocentes sin página en el PDF de profesores, reconstruidos desde el PDF de cursos:")
            for nombre, celdas in sorted(faltantes.items()):
                informe.append(f"  {nombre}: {len(celdas)} módulos (REVISAR: el export de Untis la/lo dejó afuera)")
                avisos_app.append(("aviso", f"{nombre} no tiene página en el PDF de profesores; se armó su horario con el PDF "
                                            f"de cursos ({len(celdas)} módulos). Revisá que esté bien."))
                docentes.append(parse_horario.Docente(nombre=nombre, horas="", ocupadas=set(celdas),
                                                      avisos=["tomado del PDF de cursos"]))
    else:
        informe.append("\nValidación cruzada: NO se hizo (falta --cursos)")
        avisos_app.append(("aviso", "No se eligió el horario de cursos: no se controló si falta algún docente en el de profesores."))

    if os.path.exists(args.manuales):
        manuales = horarios_manuales.cargar(args.manuales)
        repetidos = [m.nombre for m in manuales if any(maestro.misma_persona(m.nombre, d.nombre) for d in docentes)]
        detener += [f"{n}: figura en el PDF y en {args.manuales}; dejarlo en un solo lugar" for n in repetidos]
        informe.append(f"\nHorarios transcriptos a mano ({len(manuales)} docentes, de un PDF escaneado; revisar contra el original):")
        informe += [f"  {m.nombre}: {len(m.ocupadas)} módulos" for m in manuales]
        docentes += manuales

    vigentes, vencidas, futuras, sin_fin = excepciones.cargar(args.excepciones, hoy)
    lic = licencias.cargar(args.licencias, hoy)
    for l in lic["vigentes"]:  # si el docente está en el horario con otra ortografía, se usa esa
        existente = next((d.nombre for d in docentes if maestro.misma_persona(l["docente"], d.nombre)), None)
        if existente:
            l["docente"], l["clave"] = existente, clave_docente(existente)
    nombres = ([d.nombre for d in docentes] + [e["docente"] for e in vigentes]
               + [l["docente"] for l in lic["vigentes"] if l["en_lista"]])
    maes, sin_trat, discrepancias = maestro.completar_maestro(
        list(dict.fromkeys(nombres)), args.maestro, args.mdb, args.plantilla
    )
    asignacion = excepciones.aplicar(asignar(docentes), vigentes)
    fuentes_previas = [("el último libro generado", turnos_previos.cargar(args.turnos_previos))]
    if os.path.exists(args.plantilla):
        fuentes_previas.append(("el libro actual", turnos_previos.desde_listas(render_libro.leer_listas(args.plantilla))))
    notas_licencias, sin_datos = licencias.aplicar(
        asignacion, lic["vigentes"], lambda nombre: turnos_previos.buscar(nombre, *fuentes_previas)
    )
    detener += [f"{n}: tiene una licencia vigente, pero no se sabe en qué días y turnos figuraba (no estaba en el libro anterior)"
                for n in sin_datos]
    en_libro = {clave for clave, _ in asignacion}
    sin_trat = [n for n in sin_trat if clave_docente(n) in en_libro]  # a quien no va en el libro no se le exige
    if sin_trat:
        detener.append(f"falta el tratamiento (Profesor/Profesora) de: {', '.join(sin_trat)} - completarlo en {args.maestro}")
    if discrepancias:
        informe.append("\nDiscrepancias de tratamiento (se usó el .mdb):")
        informe += [f"  {d}" for d in discrepancias]
        avisos_app += [("aviso", f"Tratamiento distinto en dos fuentes: {d}") for d in discrepancias]

    informe.append(f"\nExcepciones: {len(vigentes)} vigentes, {len(vencidas)} vencidas, {len(futuras)} futuras")
    informe += [
        f"  vigente: {e['docente']} {e['turno']} {','.join(e['dias'])} | {e['motivo']} | "
        f"desde {e['desde'] or '?'} hasta {e['hasta'] or 'sin fecha de fin'}"
        for e in vigentes
    ]
    informe += [f"  SIN FECHA DE FIN: {e['docente']} {e['turno']}" for e in sin_fin]
    informe += [f"  VENCIDA (no se aplicó): {e['docente']} hasta {e['hasta']}" for e in vencidas]

    informe.append(f"\nLicencias: {len(lic['vigentes'])} vigentes, {len(lic['vencidas'])} vencidas, {len(lic['futuras'])} futuras")
    informe += [
        f"  {l['docente']} | {l['motivo'] or 'sin motivo'} | desde {l['desde'] or '?'} hasta {l['hasta'] or 'sin fecha de fin'}"
        f" | {'en la lista' if l['en_lista'] else 'fuera de la lista'}"
        for l in lic["vigentes"]
    ]
    informe += notas_licencias
    informe += [f"  SIN FECHA DE FIN: {l['docente']}" for l in lic["sin_fin"]]
    avisos_app += [("info", f"{l['docente']}: la licencia no tiene fecha de fin.") for l in lic["sin_fin"]]
    for l in lic["vencidas"]:
        tiene_clases = any(d.ocupadas and maestro.misma_persona(l["docente"], d.nombre) for d in docentes)
        if not tiene_clases:
            avisos_app.append(("aviso", f"{l['docente']}: la licencia venció el {l['hasta']:%d/%m/%Y} y no tiene clases en el "
                                        "horario, así que ya no figura en el libro. ¿Volvió o se extiende la licencia?"))
        informe.append(
            f"  VENCIDA (ya no tiene efecto): {l['docente']} hasta {l['hasta']} - "
            + ("tiene clases en el horario: figura como cualquier docente" if tiene_clases
               else "NO tiene clases en el horario: ya NO figura en el libro (¿volvió? ¿se extiende la licencia?)")
        )
    informe += [f"  FUTURA (todavía no tiene efecto): {l['docente']} desde {l['desde']}" for l in lic["futuras"]]

    en_licencia = lambda nombre: any(maestro.misma_persona(nombre, l["docente"]) for l in lic["vigentes"])  # noqa: E731
    sin_horas = [d.nombre for d in docentes if not d.ocupadas
                 and not any(clave_docente(d.nombre) == e["clave"] for e in vigentes) and not en_licencia(d.nombre)]
    if sin_horas:
        informe.append("\nDocentes en el PDF sin ninguna clase, sin licencia y sin estar excluidos (no figuran en el libro):")
        informe.append("  Qué hacer: si ya no trabajan o van en otra planilla, agregalos en Excluidos para que no vuelvan a avisar.")
        informe += [f"  {n}" for n in sin_horas]
        avisos_app += [("aviso", f"{n} está en el horario pero sin ninguna clase ni licencia: no sale en el libro. "
                                 "Si ya no trabaja, agregalo en Excluidos y deja de avisar.") for n in sin_horas]

    listas = armar_listas(asignacion, maes)
    informe.append("\nCantidad de docentes por hoja y día:")
    for turno in ("tm", "tmyt"):
        informe.append(f"  {turno:4} " + "  ".join(f"{NOMBRE_DIA[i][:3]} {len(listas[turno][i]):2}" for i in range(5)))

    if os.path.exists(args.plantilla):
        antes = render_libro.leer_listas(args.plantilla)
        en_el_libro_nuevo = [n for turno in listas.values() for dia in turno for n, _ in dia]  # con el nombre tal como se imprime
        ausentes = [n for n in ausentes_del_pdf(antes, [d.nombre for d in docentes] + en_el_libro_nuevo)
                    if not any(maestro.misma_persona(n, e["docente"]) for e in vigentes) and not en_licencia(n)]  # los explicados ya figuran arriba
        informe.append(f"\nEstán en el libro actual y NO en el horario nuevo ({len(ausentes)}):")
        informe.append("  Qué hacer: si es alguien que ya no está, nada. Si sigue, puede estar escrito distinto en el libro;"
                       " en ese caso corregí el nombre impreso en datos\\docentes.csv.")
        informe += [f"  {n}" for n in ausentes] or ["  ninguno"]
        avisos_app += [("aviso", f"{n} figuraba en el libro anterior y no aparece en el horario con ese nombre (puede estar "
                                 "escrito distinto). Si es otra persona o ya no está, no sale en el libro.")
                       for n in {clave_docente(n): n for n in ausentes}.values()]
        informe.append("\nQué cambia respecto del libro actual (+ entra en esa hoja y día, - sale):")
        informe.append("  Qué hacer: nada. Es solo para controlar que los cambios tengan sentido (por ejemplo, que salga"
                       " quien ya no tiene clases ese día). Los nombres escritos distinto ya están emparejados.")
        informe += diferencias(antes, listas) or ["  ninguna"]

    ruta_informe = os.path.join(args.salida, "informe.txt")
    conteo = {turno: [len(dia) for dia in listas[turno]] for turno in listas}
    if detener:
        informe.append("\nNO SE GENERÓ EL LIBRO:")
        informe += [f"  {d}" for d in detener]
        texto = "\n".join(informe) + "\n"
        open(ruta_informe, "w", encoding="utf-8").write(texto)
        return Resultado(False, texto, sin_tratamiento=sin_trat, problemas=detener, conteo=conteo, avisos=avisos_app)

    nombre = f"Lib. Firmas 2026 (horario {vigencia or hoy.isoformat()}).xlsx"
    ruta_libro = os.path.join(args.salida, nombre)
    render_libro.render(args.plantilla, ruta_libro, listas)
    turnos_previos.guardar(listas, args.turnos_previos)  # para que las licencias recuerden los turnos de siempre
    informe.append(f"\nGenerado: {ruta_libro}")
    texto = "\n".join(informe) + "\n"
    open(ruta_informe, "w", encoding="utf-8").write(texto)
    return Resultado(True, texto, ruta_libro=ruta_libro, conteo=conteo, avisos=avisos_app)


if __name__ == "__main__":
    sys.exit(main())
