"""Lista de preceptores: quién viene cada día, con sus licencias (hoja `prec. 2026` del libro de firmas).

`preceptores.csv` (no se versiona) tiene una fila por persona:
    apellido;nombre;cargo;dias;lic_desde;lic_hasta;lic_motivo;en_lista
    Garcia;Ana;Preceptora;lunes,martes,miercoles,jueves,viernes;;;;si
Las licencias se comportan como las de docentes (ver licencias.py): vigente y `en_lista = si` sigue en sus días; vigente y
`en_lista = no` sale de la lista; vencida o futura no tiene efecto. Van en su propio archivo: en `licencias.csv` el armado
del libro de docentes las tomaría por docentes de licencia.
"""
import repositorio
from clasificar import DIAS, clave_docente

CAMPOS = ["apellido", "nombre", "cargo", "dias", "lic_desde", "lic_hasta", "lic_motivo", "en_lista"]
_VIGENTES = ("Vigente", "Vigente, sin fecha de fin")


def leer(ruta):
    return [{c: (f.get(c) or "").strip() for c in CAMPOS} for f in repositorio._leer(ruta)]


def _dias(texto):
    pedidos = {clave_docente(d) for d in (texto or "").split(",") if d.strip()}
    desconocidos = pedidos - set(DIAS)
    if desconocidos:
        raise ValueError(f"No conozco el día {sorted(desconocidos)[0]!r}.")
    return ",".join(d for d in DIAS if d in pedidos)


def validar(fila):
    """Devuelve la fila normalizada (días en orden, fechas ISO) o lanza ValueError con un mensaje para el usuario."""
    apellido, nombre = (fila.get("apellido") or "").strip(), (fila.get("nombre") or "").strip()
    if not apellido or not nombre:
        raise ValueError("Escribí el apellido y el nombre.")
    dias = _dias(fila.get("dias"))
    if not dias:
        raise ValueError("Tildá al menos un día.")
    desde, hasta = repositorio.fecha_a_iso(fila.get("lic_desde", "")), repositorio.fecha_a_iso(fila.get("lic_hasta", ""))
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha 'Desde' es posterior a 'Hasta'.")
    en_lista = (fila.get("en_lista") or "si").strip().lower()
    if en_lista not in ("si", "no"):
        raise ValueError("'¿Sigue en la lista?' debe ser Sí o No.")
    return {"apellido": apellido, "nombre": nombre, "cargo": (fila.get("cargo") or "").strip(), "dias": dias,
            "lic_desde": desde, "lic_hasta": hasta, "lic_motivo": (fila.get("lic_motivo") or "").strip(),
            "en_lista": en_lista}


def guardar(ruta, filas):
    """Valida todo antes de escribir, para no dejar un archivo a medias."""
    validas = [validar(f) for f in filas]
    vistas = set()
    for f in validas:
        clave = clave_docente(f"{f['apellido']} {f['nombre']}")
        if clave in vistas:
            raise ValueError(f"{impreso(f)} ya está en la lista.")
        vistas.add(clave)
    repositorio._escribir(ruta, CAMPOS, validas)


def impreso(fila):
    return f"{fila['apellido'].upper()}, {fila['nombre']}"


def _licencia(fila):
    return {"desde": fila["lic_desde"], "hasta": fila["lic_hasta"]}


def tiene_licencia(fila):
    return bool(fila["lic_desde"] or fila["lic_hasta"] or fila["lic_motivo"])


def estado(fila, hoy):
    """'' si no tiene licencia; si no, el texto de Licencias (Vigente, Vencida, Todavía no empezó...)."""
    return repositorio.estado_licencia(_licencia(fila), hoy) if tiene_licencia(fila) else ""


def licencias_vigentes(filas, hoy):
    return [f for f in filas if estado(f, hoy) in _VIGENTES]


def listas_por_dia(filas, hoy):
    """[por día 0-4: [(impreso, cargo)] ordenado sin tildes]; una licencia vigente con en_lista = no saca a la persona."""
    listas = [[] for _ in DIAS]
    for f in filas:
        if f["en_lista"] == "no" and estado(f, hoy) in _VIGENTES:
            continue
        for d in f["dias"].split(","):
            listas[DIAS.index(d)].append((impreso(f), f["cargo"]))
    for dia in listas:
        dia.sort(key=lambda x: clave_docente(x[0]))
    return listas
