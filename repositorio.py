"""Lectura y escritura de los registros que la app edita (licencias y horarios a mano), sin pantalla.

Los CSV guardan fechas ISO (AAAA-MM-DD); en pantalla se muestran como dd/mm/aaaa. Cada función de guardado
valida todo antes de escribir, para no dejar un archivo a medias que después rompa la generación.
"""
import csv
import os
from datetime import date

from clasificar import DIAS
import excepciones
import horarios_manuales
import maestro
import licencias

MOTIVOS = ["licencia", "licencia por maternidad", "licencia por enfermedad", "licencia por cargo superior",
           "licencia sin goce", "otro"]
CAMPOS_MANUALES = ["docente", "dia", "modulos"]


def iso_a_fecha(texto):
    """'2026-10-28' -> '28/10/2026'; vacío queda vacío."""
    texto = (texto or "").strip()
    return date.fromisoformat(texto).strftime("%d/%m/%Y") if texto else ""


def fecha_a_iso(texto):
    """'28/10/2026' (o '28/10/26', '28-10-2026') -> '2026-10-28'. Lanza ValueError con un mensaje legible."""
    texto = (texto or "").strip()
    if not texto:
        return ""
    if len(texto) == 10 and texto[4] == "-":  # ya viene en ISO (lo guardado antes)
        try:
            return date.fromisoformat(texto).isoformat()
        except ValueError:
            pass
    partes = texto.replace("-", "/").replace(".", "/").split("/")
    try:
        dia, mes, anio = (int(p) for p in partes)
        if anio < 100:
            anio += 2000
        return date(anio, mes, dia).isoformat()
    except (ValueError, TypeError):
        raise ValueError(f"No entiendo la fecha {texto!r}. Escribila como día/mes/año, por ejemplo 28/10/2026.") from None


def _leer(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return [dict(fila) for fila in csv.DictReader(f, delimiter=";")]


def _escribir(ruta, campos, filas):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, campos, delimiter=";")
        w.writeheader()
        w.writerows(filas)


# ---------- licencias ----------

def leer_licencias(ruta):
    return [{c: (f.get(c) or "").strip() for c in licencias.CAMPOS} for f in _leer(ruta)]


def validar_licencia(lic):
    """Devuelve la licencia normalizada (fechas ISO) o lanza ValueError con un mensaje para el usuario."""
    docente = lic["docente"].strip()
    if not docente:
        raise ValueError("Elegí el docente.")
    desde, hasta = fecha_a_iso(lic.get("desde", "")), fecha_a_iso(lic.get("hasta", ""))
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha 'Desde' es posterior a 'Hasta'.")
    en_lista = (lic.get("en_lista") or "si").strip().lower()
    if en_lista not in ("si", "no"):
        raise ValueError("'En la lista' debe ser Sí o No.")
    return {"docente": docente, "desde": desde, "hasta": hasta, "motivo": (lic.get("motivo") or "").strip(),
            "en_lista": en_lista}


def guardar_licencias(ruta, filas):
    _escribir(ruta, licencias.CAMPOS, [validar_licencia(f) for f in filas])


def estado_licencia(lic, hoy):
    """Texto corto para la tabla: qué efecto tiene hoy esa licencia."""
    desde, hasta = (lic.get("desde") or "").strip(), (lic.get("hasta") or "").strip()
    hoy = hoy.isoformat()
    if desde and desde > hoy:
        return "Todavía no empezó"
    if hasta and hasta < hoy:
        return "Vencida"
    if not hasta:
        return "Vigente, sin fecha de fin"
    return "Vigente"


# ---------- horarios a mano ----------

def leer_manuales(ruta):
    return [{c: (f.get(c) or "").strip() for c in CAMPOS_MANUALES} for f in _leer(ruta)]


def validar_manual(fila):
    docente = fila["docente"].strip()
    if not docente:
        raise ValueError("Elegí el docente.")
    dia = fila["dia"].strip().lower()
    if dia not in DIAS:
        raise ValueError(f"Elegí un día de lunes a viernes (recibí {fila['dia']!r}).")
    try:
        modulos = horarios_manuales.parsear_modulos(fila["modulos"])
    except ValueError:
        raise ValueError("Los módulos van del 1 al 13. Escribí un rango o una lista, por ejemplo 1-6 o 1-4,8-9.") from None
    return {"docente": docente, "dia": dia, "modulos": ",".join(_compactar(modulos))}


def _compactar(modulos):
    """{1,2,3,8,9} -> ['1-3', '8-9']."""
    tramos, ordenados = [], sorted(modulos)
    inicio = anterior = ordenados[0]
    for m in ordenados[1:] + [None]:
        if m is not None and m == anterior + 1:
            anterior = m
            continue
        tramos.append(str(inicio) if inicio == anterior else f"{inicio}-{anterior}")
        if m is not None:
            inicio = anterior = m
    return tramos


def guardar_manuales(ruta, filas):
    _escribir(ruta, CAMPOS_MANUALES, [validar_manual(f) for f in filas])


def turno_de(modulos_texto):
    """Para mostrar en la tabla: 'Mañana', 'Tarde' o 'Mañana y tarde' según los módulos."""
    modulos = horarios_manuales.parsear_modulos(modulos_texto)
    manana, tarde = any(m <= 7 for m in modulos), any(m >= 8 for m in modulos)
    return "Mañana y tarde" if manana and tarde else "Tarde" if tarde else "Mañana"


def nombres_docentes(ruta_maestro):
    """Nombres impresos del maestro (docentes.csv), ordenados, para los desplegables."""
    return sorted({f["impreso"] for f in _leer_coma(ruta_maestro) if f.get("impreso")}, key=str.casefold)


def _leer_coma(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ---------- excluidos (docentes que no van en el libro) ----------

DIAS_TODOS = ",".join(DIAS)


def _es_exclusion(fila):
    return fila["turno"].strip() == "quitar" and fila["dias"].replace(" ", "") == DIAS_TODOS and not fila["hasta"].strip()


def leer_excluidos(ruta):
    """Docentes sacados del libro todos los días y sin fecha de fin: [{'docente', 'motivo'}]."""
    return [{"docente": f["docente"].strip(), "motivo": f["motivo"].strip()} for f in _leer(ruta) if _es_exclusion(f)]


def guardar_excluidos(ruta, filas):
    """Reemplaza las exclusiones y deja intactas las demás excepciones del archivo."""
    nuevas = []
    for f in filas:
        if not f["docente"].strip():
            raise ValueError("Elegí el docente.")
        if any(maestro.misma_persona(f["docente"], n["docente"]) for n in nuevas):
            raise ValueError(f"{f['docente'].strip()} ya está en la lista de excluidos.")
        nuevas.append({"docente": f["docente"].strip(), "dias": DIAS_TODOS, "turno": "quitar", "desde": "", "hasta": "",
                       "motivo": f.get("motivo", "").strip()})
    otras = [f for f in _leer(ruta) if not _es_exclusion(f)]
    _escribir(ruta, excepciones.CAMPOS, otras + nuevas)
