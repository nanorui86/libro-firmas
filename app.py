"""Ventana del libro de firmas: elegir el horario, armar el libro y revisar los avisos antes de imprimir.

Mismo formato que las otras apps de la escuela (Movimientos Docentes, Registro de Egresados): barra lateral índigo
con el menú, fondo gris claro y tarjetas blancas. Tiene tres pantallas: Armar libro, Licencias y Horarios a mano.
Toda la lógica vive en los otros módulos (`libro_firmas.generar`, `repositorio`); acá solo hay pantalla.
"""
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

import informe_vista
import libro_firmas
import maestro
import repositorio
import rutas
from clasificar import DIAS
from version import VERSION

# Junto al programa están entrada\ y salida\; los datos (licencias, excluidos...) pueden estar en una carpeta compartida (rutas.py).
BASE = rutas.BASE
RUTA_CONFIG = os.path.join(BASE, "app_config.json")  # PDF elegidos y duración: propio de cada PC
RUTA_LICENCIAS = rutas.en_datos("licencias.csv")
RUTA_MANUALES = rutas.en_datos("horarios_manuales.csv")
RUTA_MAESTRO = rutas.en_datos("docentes.csv")
RUTA_EXCEPCIONES = rutas.en_datos("excepciones.csv")
DURACION_INICIAL = 18.0  # segundos que tarda armar el libro; después se aprende de la última vez

# Colores y medidas de Movimientos Docentes / Registro de Egresados (Material Design, primario índigo).
INDIGO, INDIGO_OSCURO, INDIGO_SUAVE = "#3F51B5", "#283593", "#E8EAF6"
LATERAL_SEL, LATERAL_HOVER = "#6574C4", "#5565BE"      # blanco al 20 % y al 10 % sobre el índigo
FONDO, TARJETA, BORDE = "#FAFAFA", "#FFFFFF", "#E0E0E0"
TEXTO, TENUE = "#212121", "#6B6B6B"
VERDE, AMBAR, ROJO = "#2E7D32", "#8A5A00", "#B3261E"
AVISO_FONDO, AVISO_TEXTO = "#FFF8E1", "#5D4300"
INSIGNIA = "#FFC107"
FUENTE = "Segoe UI"
NOMBRES_DIA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
NOMBRES_DIA_SIN_TILDE = list(DIAS)

COMO_IMPRIMIR = (
    ("1", "Tocá \"Abrir en Excel para imprimir\". Se abre el libro recién armado."),
    ("2", "En Excel: Archivo > Imprimir. En qué imprimir elegí \"Imprimir todo el libro\" (así salen las dos hojas: "
          "mañana, y mañana y tarde)."),
    ("3", "Dejá la escala en 100 % (\"Sin escala\"; no uses \"Ajustar a una página\") y el papel en A4 vertical. Los "
          "renglones miden lo mismo que los del libro de papel y por eso no se achica nada."),
    ("4", "Cada hoja sale en varias páginas: una con Lunes y Martes, otra con Miércoles y Jueves, otra con Viernes, y "
          "los renglones del 24 en adelante en la página siguiente. Cada página cae sobre una tira del libro."),
    ("5", "La primera vez imprimí una sola página y apoyala sobre el libro de papel, a contraluz, para ver que los "
          "renglones coinciden. Si coinciden, ya podés imprimir todo."),
)


# ---------- configuración ----------

def leer_config():
    try:
        with open(RUTA_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar_config(config):
    try:
        os.makedirs(os.path.dirname(RUTA_CONFIG), exist_ok=True)
        with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=1)
    except OSError:
        pass  # recordar las rutas es una comodidad; no vale una ventana de error


# ---------- estilo ----------

def aplicar_estilo(raiz):
    raiz.configure(bg=FONDO)
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure(".", background=FONDO, foreground=TEXTO, font=(FUENTE, 10), bordercolor=BORDE,
                lightcolor=FONDO, darkcolor=FONDO, focuscolor=FONDO)
    s.configure("TFrame", background=FONDO)
    s.configure("Tarjeta.TFrame", background=TARJETA)
    s.configure("TLabel", background=FONDO, foreground=TEXTO)
    s.configure("Tarjeta.TLabel", background=TARJETA)
    s.configure("Tenue.TLabel", foreground=TENUE)
    s.configure("TenueT.TLabel", background=TARJETA, foreground=TENUE)
    s.configure("Titulo.TLabel", font=(FUENTE, 17, "bold"))
    s.configure("Seccion.TLabel", background=TARJETA, foreground=TENUE, font=(FUENTE, 8, "bold"))
    s.configure("Ok.TLabel", background=TARJETA, foreground=VERDE)
    s.configure("Ambar.TLabel", background=TARJETA, foreground=AMBAR)
    s.configure("Error.TLabel", background=TARJETA, foreground=ROJO)
    # Botón principal (relleno índigo) y secundario (contorno), como en las otras apps.
    s.configure("TButton", padding=(14, 7), background=TARJETA, foreground=INDIGO, bordercolor=INDIGO, borderwidth=1,
                font=(FUENTE, 10, "bold"))
    s.map("TButton", background=[("active", INDIGO_SUAVE), ("disabled", TARJETA)],
          foreground=[("disabled", "#9E9E9E")], bordercolor=[("disabled", BORDE)])
    s.configure("Primario.TButton", background=INDIGO, foreground="#FFFFFF", bordercolor=INDIGO, padding=(20, 9))
    s.map("Primario.TButton", background=[("active", INDIGO_OSCURO), ("disabled", "#C5CAE9")],
          foreground=[("disabled", "#FFFFFF")], bordercolor=[("disabled", "#C5CAE9")])
    s.configure("TEntry", fieldbackground=TARJETA, padding=6, bordercolor="#9E9E9E")
    s.map("TEntry", bordercolor=[("focus", INDIGO)])
    s.configure("TCombobox", fieldbackground=TARJETA, padding=6, bordercolor="#9E9E9E", arrowcolor=TENUE)
    s.map("TCombobox", bordercolor=[("focus", INDIGO)])
    s.configure("Treeview", background=TARJETA, fieldbackground=TARJETA, rowheight=30, bordercolor=BORDE, borderwidth=0)
    s.configure("Treeview.Heading", background=TARJETA, foreground=TENUE, font=(FUENTE, 9, "bold"), padding=(6, 8),
                relief="flat", bordercolor=BORDE)
    s.map("Treeview.Heading", background=[("active", TARJETA)])
    s.map("Treeview", background=[("selected", INDIGO_SUAVE)], foreground=[("selected", INDIGO_OSCURO)])
    s.configure("Horizontal.TProgressbar", background=INDIGO, troughcolor="#E8EAF6", bordercolor="#E8EAF6")
    s.configure("Vertical.TScrollbar", background="#E0E0E0", troughcolor=TARJETA, bordercolor=TARJETA, arrowcolor=TENUE)


class Tarjeta(tk.Frame):
    """Cuadro blanco con borde fino y, opcionalmente, la etiqueta de sección en mayúsculas."""

    def __init__(self, padre, titulo=None, **grid):
        super().__init__(padre, bg=BORDE)
        self.interior = ttk.Frame(self, style="Tarjeta.TFrame", padding=(20, 16))
        self.interior.pack(fill="both", expand=True, padx=1, pady=1)
        if titulo:
            ttk.Label(self.interior, text=titulo.upper(), style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))


class Aviso(tk.Frame):
    """Franja ámbar con ícono de información, como la de Configuración de Movimientos."""

    def __init__(self, padre, texto, ancho=700):
        super().__init__(padre, bg=AVISO_FONDO, padx=12, pady=8)
        tk.Label(self, text="ⓘ", bg=AVISO_FONDO, fg=AVISO_TEXTO, font=(FUENTE, 12)).pack(side="left", padx=(0, 8))
        tk.Label(self, text=texto, bg=AVISO_FONDO, fg=AVISO_TEXTO, font=(FUENTE, 9), wraplength=ancho,
                 justify="left").pack(side="left", fill="x")


class Pantalla(ttk.Frame):
    """Una sección del menú: título grande, subtítulo atenuado y el contenido debajo."""

    def __init__(self, padre, titulo, subtitulo):
        super().__init__(padre, padding=(26, 20, 26, 14))
        cab = ttk.Frame(self)
        cab.pack(fill="x", pady=(0, 14))
        ttk.Label(cab, text=titulo, style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(cab, text=subtitulo, style="Tenue.TLabel").pack(anchor="w", pady=(1, 0))


# ---------- formulario y tabla editable ----------

class Formulario(tk.Toplevel):
    """Ventana modal con un campo por columna. `campos`: [(clave, etiqueta, valores_del_desplegable | None)]."""

    def __init__(self, padre, titulo, campos, valores, ayuda="", validar=None):
        super().__init__(padre)
        self.title(titulo)
        self.configure(bg=TARJETA, padx=24, pady=20)
        self.resizable(False, False)
        self.transient(padre.winfo_toplevel())
        self.resultado, self._validar, self._vars = None, validar, {}
        ttk.Label(self, text=titulo, style="Titulo.TLabel", background=TARJETA).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        for i, (clave, etiqueta, opciones) in enumerate(campos, start=1):
            ttk.Label(self, text=etiqueta, style="Tarjeta.TLabel").grid(row=i, column=0, sticky="w", padx=(0, 14), pady=5)
            var = self._vars[clave] = tk.StringVar(value=valores.get(clave, ""))
            if opciones is None:
                widget = ttk.Entry(self, textvariable=var, width=36)
            else:
                widget = ttk.Combobox(self, textvariable=var, values=opciones, width=34)
            widget.grid(row=i, column=1, sticky="ew", pady=5)
            if i == 1:
                widget.focus_set()
        fila = len(campos) + 1
        if ayuda:
            ttk.Label(self, text=ayuda, style="TenueT.TLabel", wraplength=400, justify="left").grid(
                row=fila, column=0, columnspan=2, sticky="w", pady=(8, 0))
            fila += 1
        self._error = ttk.Label(self, text="", style="Error.TLabel", wraplength=400, justify="left")
        self._error.grid(row=fila, column=0, columnspan=2, sticky="w", pady=(8, 0))
        botones = ttk.Frame(self, style="Tarjeta.TFrame")
        botones.grid(row=fila + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(botones, text="Guardar", style="Primario.TButton", command=self._aceptar).pack(side="right")
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self._aceptar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        raiz = padre.winfo_toplevel()
        x = raiz.winfo_rootx() + (raiz.winfo_width() - self.winfo_width()) // 2
        y = raiz.winfo_rooty() + max(40, (raiz.winfo_height() - self.winfo_height()) // 3)
        self.geometry(f"+{max(x, 0)}+{y}")
        self.grab_set()
        self.wait_window()

    def _aceptar(self):
        valores = {k: v.get().strip() for k, v in self._vars.items()}
        try:
            if self._validar:
                valores = self._validar(valores)
        except ValueError as e:
            self._error.configure(text=str(e))
            return
        self.resultado = valores
        self.destroy()


class TablaEditable(ttk.Frame):
    """Lista con Agregar / Editar / Quitar que guarda cada cambio en disco apenas se hace."""

    ayuda_formulario = ""

    def __init__(self, padre, columnas, campos, leer, guardar, opciones=None, validar=None, vista=None):
        """columnas: [(clave, título, ancho)]; campos: ver Formulario; leer() -> filas; guardar(filas);
        vista(fila) -> dict con lo que se muestra (por defecto, la fila misma)."""
        super().__init__(padre)
        self.columnas, self.campos, self.leer, self.guardar = columnas, campos, leer, guardar
        self.opciones = opciones or (lambda: {})
        self.validar, self.vista = validar, vista or (lambda f: f)
        self.vista_para_editar = lambda fila: fila
        self.filas = []
        tarjeta = Tarjeta(self)
        tarjeta.pack(fill="both", expand=True)
        cuerpo = ttk.Frame(tarjeta.interior, style="Tarjeta.TFrame")
        cuerpo.pack(fill="both", expand=True)
        self.arbol = ttk.Treeview(cuerpo, columns=[c[0] for c in columnas], show="headings", selectmode="browse")
        for clave, titulo, ancho in columnas:
            self.arbol.heading(clave, text=titulo, anchor="w")
            self.arbol.column(clave, width=ancho, minwidth=60, anchor="w", stretch=clave == columnas[-1][0])
        barra = ttk.Scrollbar(cuerpo, orient="vertical", command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.arbol.bind("<Double-1>", lambda _e: self.editar())
        self.arbol.tag_configure("apagada", foreground="#9E9E9E")
        botones = ttk.Frame(tarjeta.interior, style="Tarjeta.TFrame")
        botones.pack(fill="x", pady=(14, 0))
        ttk.Button(botones, text="Agregar", style="Primario.TButton", command=self.agregar).pack(side="left")
        ttk.Button(botones, text="Editar", command=self.editar).pack(side="left", padx=8)
        ttk.Button(botones, text="Quitar", command=self.quitar).pack(side="left")
        self.recargar()

    def recargar(self):
        try:
            self.filas = self.leer()
        except (ValueError, OSError) as e:
            messagebox.showerror("No se pudo leer el archivo", str(e), parent=self)
            self.filas = []
        self.arbol.delete(*self.arbol.get_children())
        for i, fila in enumerate(self.filas):
            v = self.vista(fila)
            tags = ("apagada",) if v.get("_apagada") else ()
            self.arbol.insert("", "end", iid=str(i), values=[v.get(c[0], "") for c in self.columnas], tags=tags)

    def _seleccion(self):
        sel = self.arbol.selection()
        if not sel:
            messagebox.showinfo("Elegí una fila", "Primero elegí una fila de la lista.", parent=self)
            return None
        return int(sel[0])

    def _formulario(self, titulo, valores):
        opciones = self.opciones()
        campos = [(clave, etiqueta, opciones.get(clave)) for clave, etiqueta, _ in self.campos]
        return Formulario(self, titulo, campos, valores, ayuda=self.ayuda_formulario, validar=self.validar).resultado

    def _guardar_con(self, nuevas):
        try:
            self.guardar(nuevas)
        except (ValueError, OSError) as e:
            messagebox.showerror("No se guardó", str(e), parent=self)
            return False
        self.recargar()
        return True

    def _al_dia(self):
        """True si el archivo sigue igual que lo que se ve; si otra PC lo cambió, actualiza la lista y avisa."""
        try:
            igual = self.leer() == self.filas
        except (ValueError, OSError):
            return True  # si no se puede leer, que el guardado informe el problema
        if not igual:
            self.recargar()
            messagebox.showinfo("La lista cambió", "Alguien modificó esta lista desde otra PC. Se actualizó lo que ves: "
                                "revisala y repetí la acción.", parent=self)
        return igual

    def agregar(self):
        if not self._al_dia():
            return
        nueva = self._formulario("Agregar", {})
        if nueva and self._al_dia():
            self._guardar_con(self.filas + [nueva])

    def editar(self):
        if not self._al_dia():
            return
        i = self._seleccion()
        if i is None:
            return
        nueva = self._formulario("Editar", self.vista_para_editar(self.filas[i]))
        if nueva and self._al_dia():
            self._guardar_con(self.filas[:i] + [nueva] + self.filas[i + 1:])

    def quitar(self):
        if not self._al_dia():
            return
        i = self._seleccion()
        if i is None:
            return
        if messagebox.askyesno("Quitar", "¿Quitar esta fila de la lista?", parent=self) and self._al_dia():
            self._guardar_con(self.filas[:i] + self.filas[i + 1:])


def pantalla_licencias(padre):
    hoy = date.today()
    pantalla = Pantalla(padre, "Licencias", "Docentes que siguen en la lista mientras dura su licencia")
    Aviso(pantalla, "Mientras una licencia esté vigente, el docente sigue en la lista, en los mismos días y turnos de "
                    "siempre, aunque el horario nuevo ya no lo traiga. Si ponés \"No\" en ¿Sigue en la lista?, sale del "
                    "libro. Las fechas van como día/mes/año; \"Hasta\" puede quedar vacío si todavía no se sabe.",
          ancho=760).pack(fill="x", pady=(0, 12))

    def vista(f):
        estado = repositorio.estado_licencia(f, hoy)
        return {"docente": f["docente"], "desde": repositorio.iso_a_fecha(f["desde"]),
                "hasta": repositorio.iso_a_fecha(f["hasta"]), "motivo": f["motivo"],
                "en_lista": "Sí" if f["en_lista"] != "no" else "No", "estado": estado, "_apagada": estado == "Vencida"}

    def validar(v):
        return repositorio.validar_licencia(dict(v, en_lista="no" if v["en_lista"].lower().startswith("n") else "si"))

    t = TablaEditable(
        pantalla,
        columnas=[("docente", "Docente", 190), ("desde", "Desde", 85), ("hasta", "Hasta", 85), ("motivo", "Motivo", 170),
                  ("en_lista", "¿Sigue en la lista?", 125), ("estado", "Estado hoy", 160)],
        campos=[("docente", "Docente", None), ("desde", "Desde", None), ("hasta", "Hasta", None),
                ("motivo", "Motivo", None), ("en_lista", "¿Sigue en la lista?", None)],
        leer=lambda: repositorio.leer_licencias(RUTA_LICENCIAS),
        guardar=lambda filas: repositorio.guardar_licencias(RUTA_LICENCIAS, filas),
        opciones=lambda: {"docente": repositorio.nombres_docentes(RUTA_MAESTRO), "motivo": repositorio.MOTIVOS,
                          "en_lista": ["Sí", "No"]},
        validar=validar, vista=vista)
    t.vista_para_editar = lambda f: dict(f, desde=repositorio.iso_a_fecha(f["desde"]),
                                         hasta=repositorio.iso_a_fecha(f["hasta"]),
                                         en_lista="Sí" if f["en_lista"] != "no" else "No")
    t.ayuda_formulario = "Podés escribir el nombre si no está en la lista, como Apellido, Nombre."
    t.pack(fill="both", expand=True)
    pantalla.al_mostrar = t.recargar
    return pantalla


def pantalla_manuales(padre):
    pantalla = Pantalla(padre, "Horarios a mano", "Docentes cuyo horario viene en un PDF escaneado o en una foto")
    Aviso(pantalla, "Una fila por docente y día (hoy, los de inglés). Cuando ese horario cambie hay que cargarlo de "
                    "nuevo. Módulos: un rango o una lista, por ejemplo 1-6 o 1-4,8-9.", ancho=760).pack(fill="x", pady=(0, 12))

    def vista(f):
        try:
            turno = repositorio.turno_de(f["modulos"])
        except ValueError:
            turno = "revisar"
        return {"docente": f["docente"], "dia": f["dia"].capitalize(), "modulos": f["modulos"], "turno": turno}

    t = TablaEditable(
        pantalla,
        columnas=[("docente", "Docente", 250), ("dia", "Día", 110), ("modulos", "Módulos", 150), ("turno", "Turno", 150)],
        campos=[("docente", "Docente", None), ("dia", "Día", None), ("modulos", "Módulos", None)],
        leer=lambda: repositorio.leer_manuales(RUTA_MANUALES),
        guardar=lambda filas: repositorio.guardar_manuales(RUTA_MANUALES, filas),
        opciones=lambda: {"docente": repositorio.nombres_docentes(RUTA_MAESTRO),
                          "dia": [d.capitalize() for d in NOMBRES_DIA_SIN_TILDE]},
        validar=repositorio.validar_manual, vista=vista)
    t.ayuda_formulario = ("Del módulo 1 al 7 es la mañana (hasta las 13:05) y del 8 al 13 la tarde. Con cualquier "
                          "módulo de la tarde, ese día va en la hoja de mañana y tarde.")
    t.vista_para_editar = lambda f: dict(f, dia=f["dia"].capitalize())
    t.pack(fill="both", expand=True)
    pantalla.al_mostrar = t.recargar
    return pantalla


def pantalla_excluidos(padre):
    pantalla = Pantalla(padre, "Excluidos", "Docentes que no van en el libro aunque estén en el horario")
    Aviso(pantalla, "Sirve para quien figura en el PDF de Untis pero no firma en este libro: ya no trabaja, o va en la "
                    "planilla de preceptores (por ejemplo, el ayudante de laboratorio). Un docente excluido no sale en "
                    "ningún día y el programa deja de avisar por él.", ancho=760).pack(fill="x", pady=(0, 12))
    t = TablaEditable(
        pantalla,
        columnas=[("docente", "Docente", 300), ("motivo", "Motivo", 400)],
        campos=[("docente", "Docente", None), ("motivo", "Motivo", None)],
        leer=lambda: repositorio.leer_excluidos(RUTA_EXCEPCIONES),
        guardar=lambda filas: repositorio.guardar_excluidos(RUTA_EXCEPCIONES, filas),
        opciones=lambda: {"docente": [n for n in repositorio.nombres_docentes(RUTA_MAESTRO)
                                      if not any(maestro.misma_persona(n, f["docente"]) for f in t.filas)]},
        validar=lambda v: v)
    t.ayuda_formulario = ("Elegí el docente de la lista (no aparecen los que ya están excluidos) o escribilo como figura "
                          "en Untis: Apellido, Nombre.")
    t.pack(fill="both", expand=True)
    pantalla.al_mostrar = t.recargar
    return pantalla


# ---------- docentes por día ----------

class Renglones(tk.Canvas):
    """Docentes por día en cada hoja, con renglones como los del libro."""

    def __init__(self, padre):
        super().__init__(padre, height=140, bg=TARJETA, highlightthickness=0)
        self.bind("<Configure>", lambda _e: self.dibujar())
        self.conteo = None

    def mostrar(self, conteo):
        self.conteo = conteo
        self.dibujar()

    def dibujar(self):
        self.delete("all")
        w = max(self.winfo_width(), 400)
        izq, ancho_col = 170, (w - 170) / 5
        for y in (36, 36 + 52, 36 + 104):
            self.create_line(0, y, w, y, fill="#E0E0E0")
        for i, dia in enumerate(NOMBRES_DIA):
            self.create_text(izq + ancho_col * (i + 0.5), 18, text=dia, font=(FUENTE, 10, "bold"), fill=TENUE)
        for fila, (clave, etiqueta) in enumerate((("tm", "Hoja mañana"), ("tmyt", "Hoja mañana y tarde"))):
            y = 62 + 52 * fila
            self.create_text(0, y, text=etiqueta, anchor="w", font=(FUENTE, 10), fill=TEXTO)
            for i in range(5):
                n = self.conteo[clave][i] if self.conteo else "–"
                self.create_text(izq + ancho_col * (i + 0.5), y, text=str(n), font=(FUENTE, 22, "bold"), fill=INDIGO_OSCURO)


# ---------- pantalla principal ----------

class PantallaArmar(Pantalla):
    def __init__(self, padre, app):
        super().__init__(padre, "Armar libro", "Listas de mañana y de mañana y tarde a partir del horario de Untis")
        self.app, self.cola, self.ruta_libro, self.informe = app, queue.Queue(), None, ""
        config = leer_config()
        self.var_prof = tk.StringVar(value=config.get("profesores", ""))
        self.var_cursos = tk.StringVar(value=config.get("cursos", ""))

        t1 = Tarjeta(self, "Horario")
        t1.pack(fill="x", pady=(0, 12))
        form = ttk.Frame(t1.interior, style="Tarjeta.TFrame")
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self._selector(form, 0, "Profesores (PDF de Untis)", self.var_prof)
        self._selector(form, 1, "Cursos (para controlar)", self.var_cursos, opcional=True)
        acciones = ttk.Frame(form, style="Tarjeta.TFrame")
        acciones.grid(row=2, column=0, columnspan=3, sticky="w", pady=(14, 0))
        self.boton = ttk.Button(acciones, text="Armar libro", style="Primario.TButton", command=self.armar)
        self.boton.pack(side="left")
        self.estado = ttk.Label(acciones, text="", style="TenueT.TLabel")
        self.estado.pack(side="left", padx=16)
        self.barra = ttk.Progressbar(acciones, mode="determinate", maximum=100, length=220)
        self.inicio, self.duracion_estimada = None, DURACION_INICIAL

        t2 = Tarjeta(self, "Docentes por día")
        t2.pack(fill="x", pady=(0, 12))
        self.renglones = Renglones(t2.interior)
        self.renglones.pack(fill="x")
        self.renglones.mostrar(None)

        t3 = Tarjeta(self, "Para revisar antes de imprimir")
        t3.pack(fill="both", expand=True, pady=(0, 12))
        marco = ttk.Frame(t3.interior, style="Tarjeta.TFrame")
        marco.pack(fill="both", expand=True)
        self.avisos = tk.Text(marco, height=6, wrap="word", bg=TARJETA, fg=TEXTO, relief="flat", font=(FUENTE, 10),
                              padx=0, pady=2, state="disabled", highlightthickness=0, cursor="arrow")
        barra = ttk.Scrollbar(marco, command=self.avisos.yview)
        self.avisos.configure(yscrollcommand=barra.set)
        self.avisos.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.avisos.tag_configure("error", foreground=ROJO, font=(FUENTE, 10, "bold"), spacing3=4)
        self.avisos.tag_configure("aviso", foreground=AMBAR, spacing3=4)
        self.avisos.tag_configure("info", foreground=TENUE, spacing3=4)
        self.avisos.tag_configure("ok", foreground=VERDE, font=(FUENTE, 10, "bold"), spacing3=6)
        self._escribir_avisos([("info", "Elegí el PDF de profesores y tocá Armar libro. Acá aparece lo que conviene "
                                        "mirar antes de imprimir.")])

        pie = ttk.Frame(self)
        pie.pack(fill="x")
        self.b_excel = ttk.Button(pie, text="Abrir en Excel para imprimir", style="Primario.TButton",
                                  command=self.abrir_libro, state="disabled")
        self.b_excel.pack(side="left")
        self.b_carpeta = ttk.Button(pie, text="Abrir carpeta", command=self.abrir_carpeta, state="disabled")
        self.b_carpeta.pack(side="left", padx=8)
        self.b_informe = ttk.Button(pie, text="Ver informe completo", command=self.ver_informe, state="disabled")
        self.b_informe.pack(side="left")
        ttk.Button(pie, text="Cómo imprimir", command=self.como_imprimir).pack(side="right")

    def _selector(self, marco, fila, etiqueta, var, opcional=False):
        ttk.Label(marco, text=etiqueta, style="Tarjeta.TLabel").grid(row=fila, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(marco, textvariable=var).grid(row=fila, column=1, sticky="ew", pady=5)
        botones = ttk.Frame(marco, style="Tarjeta.TFrame")
        botones.grid(row=fila, column=2, padx=(10, 0))
        ttk.Button(botones, text="Examinar…", command=lambda: self._elegir(var)).pack(side="left")
        if opcional:
            ttk.Button(botones, text="Borrar", command=lambda: var.set("")).pack(side="left", padx=(6, 0))

    def _elegir(self, var):
        inicial = os.path.dirname(var.get()) if var.get() else os.path.join(BASE, "entrada")
        ruta = filedialog.askopenfilename(parent=self, title="Elegir PDF", filetypes=[("PDF", "*.pdf")],
                                          initialdir=inicial if os.path.isdir(inicial) else BASE)
        if ruta:
            var.set(os.path.normpath(ruta))

    def _escribir_avisos(self, avisos):
        self.avisos.configure(state="normal")
        self.avisos.delete("1.0", "end")
        marca = {"error": "✖  ", "aviso": "⚠  ", "info": "•  ", "ok": "✔  "}
        for nivel, texto in avisos:
            self.avisos.insert("end", marca[nivel] + texto + "\n", nivel)
        self.avisos.configure(state="disabled")

    # --- armado ---

    def armar(self):
        profesores, cursos = self.var_prof.get().strip(), self.var_cursos.get().strip()
        if not os.path.isfile(profesores):
            messagebox.showwarning("Falta el horario", "Elegí el PDF de profesores (el que baja de Untis).", parent=self)
            return
        if cursos and not os.path.isfile(cursos):
            messagebox.showwarning("No encuentro el PDF de cursos",
                                   "Elegí otro PDF de cursos o tocá Borrar para armar sin él.", parent=self)
            return
        config = leer_config()
        guardar_config({**config, "profesores": profesores, "cursos": cursos})
        self.duracion_estimada = float(config.get("duracion", DURACION_INICIAL))
        self.boton.configure(state="disabled")
        for b in (self.b_excel, self.b_carpeta, self.b_informe):
            b.configure(state="disabled")
        self.inicio = time.monotonic()
        self.barra.configure(value=0)
        self.barra.pack(side="left", padx=(16, 0), after=self.boton)
        self._contar()
        args = libro_firmas.opciones(profesores, base=BASE, cursos=cursos or None)
        threading.Thread(target=self._trabajo, args=(args,), daemon=True).start()
        self.after(150, self._esperar)

    def _contar(self):
        """Segundos transcurridos y barra que avanza de corrido mientras se arma.

        No hay una medida real del avance, así que la barra sigue el tiempo que tardó la vez anterior: sube rápido
        al principio, se frena cerca del final y nunca llega al 100 % hasta que termina de verdad."""
        if self.inicio is None:
            return
        transcurrido = time.monotonic() - self.inicio
        self.barra.configure(value=97 * (1 - math.exp(-2.0 * transcurrido / self.duracion_estimada)))
        self.estado.configure(text=f"Armando el libro…  {int(transcurrido)} s   (tarda unos {round(self.duracion_estimada)} segundos)")
        self.after(100, self._contar)

    def _trabajo(self, args):
        try:
            self.cola.put(("ok", libro_firmas.generar(args)))
        except Exception as e:  # lo que sea se muestra en pantalla; el hilo no puede morir en silencio
            self.cola.put(("error", e))

    def _esperar(self):
        try:
            tipo, valor = self.cola.get_nowait()
        except queue.Empty:
            self.after(150, self._esperar)
            return
        if tipo == "ok":
            guardar_config({**leer_config(), "duracion": round(time.monotonic() - self.inicio, 1)})
        self.inicio = None
        self.barra.configure(value=100)
        self.after(500, self.barra.pack_forget)
        self.boton.configure(state="normal")
        if tipo == "error":
            self.estado.configure(text="")
            self._escribir_avisos([("error", f"No se pudo armar el libro: {valor}")])
            messagebox.showerror("No se pudo armar el libro", str(valor), parent=self)
            return
        self._mostrar(valor)

    def _mostrar(self, r):
        self.informe = r.informe
        self.b_informe.configure(state="normal")
        if r.conteo:
            self.renglones.mostrar(r.conteo)
        if not r.ok and r.sin_tratamiento:
            self.estado.configure(text="Falta un dato.")
            if self._preguntar_tratamientos(r.sin_tratamiento):
                self.armar()
                return
        if not r.ok:
            self.estado.configure(text="No se armó el libro.")
            self._escribir_avisos([("error", p) for p in r.problemas]
                                  or [("error", "No se pudo armar el libro. Mirá el informe completo.")])
            return
        self.ruta_libro = r.ruta_libro
        self.b_excel.configure(state="normal")
        self.b_carpeta.configure(state="normal")
        self.app.ruta_libro = r.ruta_libro
        self.estado.configure(text="Libro armado.")
        cabecera = [("ok", "Libro armado. Antes de imprimir, mirá esto:" if r.avisos else "Libro armado, sin nada para revisar.")]
        self._escribir_avisos(cabecera + sorted(r.avisos, key=lambda a: a[0] != "aviso"))

    def _preguntar_tratamientos(self, nombres):
        for nombre in nombres:
            r = messagebox.askyesnocancel(
                "¿Profesor o Profesora?",
                f"No sé cómo tratar a:\n\n{nombre}\n\nSí = Profesora\nNo = Profesor\nCancelar = lo decido después",
                parent=self)
            if r is None:
                return False
            maestro.fijar_tratamiento(RUTA_MAESTRO, nombre, "Profesora" if r else "Profesor")
        return True

    # --- botones de abajo ---

    def abrir_libro(self):
        if self.ruta_libro and os.path.exists(self.ruta_libro):
            os.startfile(self.ruta_libro)

    def abrir_carpeta(self):
        if self.ruta_libro:
            os.startfile(os.path.dirname(self.ruta_libro))

    def ver_informe(self):
        VentanaInforme(self, self.informe)

    def como_imprimir(self):
        ventana = tk.Toplevel(self)
        ventana.title("Cómo imprimir")
        ventana.configure(bg=TARJETA, padx=26, pady=22)
        ventana.transient(self.winfo_toplevel())
        ttk.Label(ventana, text="Cómo imprimir el libro", style="Titulo.TLabel", background=TARJETA).pack(anchor="w", pady=(0, 12))
        for numero, texto in COMO_IMPRIMIR:
            fila = ttk.Frame(ventana, style="Tarjeta.TFrame")
            fila.pack(fill="x", pady=5)
            tk.Label(fila, text=numero, bg=INDIGO, fg="#FFFFFF", font=(FUENTE, 10, "bold"), width=2).pack(side="left", anchor="n", padx=(0, 12))
            ttk.Label(fila, text=texto, style="Tarjeta.TLabel", wraplength=500, justify="left").pack(side="left")
        Aviso(ventana, "Las firmas se hacen en el libro de papel, no en esta hoja.", ancho=520).pack(fill="x", pady=(14, 0))
        ttk.Button(ventana, text="Entendido", style="Primario.TButton", command=ventana.destroy).pack(anchor="e", pady=(16, 0))


# ---------- ventana ----------

class VentanaInforme(tk.Toplevel):
    """El informe de la corrida como tarjetas: una por sección, con lo que hay que hacer y filas legibles."""

    HOJAS = {"tm": "Mañana", "tmyt": "Mañana y tarde"}

    def __init__(self, padre, texto):
        super().__init__(padre)
        self.title("Informe completo")
        self.configure(bg=FONDO)
        self.geometry("940x720")
        self.minsize(760, 480)
        self.transient(padre.winfo_toplevel())
        encabezado, secciones = informe_vista.parsear(texto)
        lienzo = tk.Canvas(self, bg=FONDO, highlightthickness=0)
        barra = ttk.Scrollbar(self, command=lienzo.yview)
        lienzo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        lienzo.pack(side="left", fill="both", expand=True)
        cuerpo = ttk.Frame(lienzo, padding=(26, 20, 26, 20))
        ventana_id = lienzo.create_window(0, 0, window=cuerpo, anchor="nw")
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana_id, width=e.width))
        cuerpo.bind("<Configure>", lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        self.bind("<MouseWheel>", lambda e: lienzo.yview_scroll(-1 * (e.delta // 120), "units"))
        ttk.Label(cuerpo, text="Informe completo", style="Titulo.TLabel").pack(anchor="w")
        for linea in encabezado:
            ttk.Label(cuerpo, text=linea, style="Tenue.TLabel").pack(anchor="w")
        ttk.Label(cuerpo, text="Cada tarjeta es una parte de la revisión. Debajo del título dice qué hacer; si dice "
                               "\"nada\", es solo información.", style="Tenue.TLabel").pack(anchor="w", pady=(6, 14))
        for sec in secciones:
            self._tarjeta(cuerpo, sec).pack(fill="x", pady=(0, 12))

    def _tarjeta(self, padre, sec):
        color = {"error": ROJO}.get(sec["tipo"], TENUE)
        t = Tarjeta(padre)
        cab = ttk.Frame(t.interior, style="Tarjeta.TFrame")
        cab.pack(fill="x")
        tk.Label(cab, text=sec["titulo"].upper(), bg=TARJETA, fg=color, font=(FUENTE, 8, "bold"), anchor="w").pack(side="left")
        if sec["detalle"]:
            tk.Label(cab, text=sec["detalle"], bg=INDIGO_SUAVE, fg=INDIGO_OSCURO, font=(FUENTE, 9, "bold"), padx=8).pack(side="right")
        if sec["ayuda"]:
            ttk.Label(t.interior, text=sec["ayuda"], style="TenueT.TLabel", wraplength=800, justify="left").pack(anchor="w", pady=(6, 0))
        marco = ttk.Frame(t.interior, style="Tarjeta.TFrame")
        marco.pack(fill="x", pady=(10, 0))
        if sec["tipo"] == "cambios":
            self._cambios(marco, sec["filas"])
        elif sec["tipo"] == "conteo":
            self._conteo(marco, sec["filas"])
        else:
            self._lista(marco, sec["filas"], error=sec["tipo"] == "error")
        return t

    def _lista(self, marco, filas, error=False):
        if not filas:
            return
        texto = tk.Text(marco, wrap="word", bg=TARJETA, fg=TEXTO, relief="flat", font=(FUENTE, 10), padx=0, pady=0,
                        highlightthickness=0, cursor="arrow", height=1)
        texto.tag_configure("nombre", font=(FUENTE, 10, "bold"))
        texto.tag_configure("revisar", foreground=AMBAR)
        texto.tag_configure("error", foreground=ROJO)
        texto.tag_configure("pauta", spacing3=5)
        for fila in filas:
            for prefijo in ("aviso ", "ERROR "):
                if fila.startswith(prefijo):
                    fila = fila[len(prefijo):]
            nombre, dos_puntos, resto = fila.partition(": ")
            alerta = "error" if error or fila.startswith("ERROR") else "revisar" if ("REVISAR" in fila or fila.startswith("VENCIDA")) else None
            tags = ("pauta",) + ((alerta,) if alerta else ())
            texto.insert("end", "•  ", tags)
            if dos_puntos and len(nombre) < 60:
                texto.insert("end", nombre, tags + ("nombre",))
                texto.insert("end", ": " + resto + "\n", tags)
            else:
                texto.insert("end", fila + "\n", tags)
        texto.configure(state="disabled")
        texto.pack(fill="x")
        texto.bind("<Configure>", lambda _e, t=texto: self._ajustar_alto(t))

    @staticmethod
    def _ajustar_alto(texto):
        """Alto justo para el texto ya partido en renglones (depende del ancho de la ventana)."""
        lineas = texto.count("1.0", "end", "displaylines")
        alto = max(1, lineas[0] if lineas else 1)
        if int(texto.cget("height")) != alto:
            texto.configure(height=alto)

    def _cambios(self, marco, filas):
        if not filas:
            ttk.Label(marco, text="Sin cambios.", style="TenueT.TLabel").pack(anchor="w")
            return
        for c, (titulo, ancho) in enumerate((("", 70), ("Hoja", 130), ("Día", 100), ("Docente", 400))):
            tk.Label(marco, text=titulo, bg=TARJETA, fg=TENUE, font=(FUENTE, 9, "bold"), anchor="w", width=ancho // 8).grid(
                row=0, column=c, sticky="w", padx=(0, 6))
        for r, (signo, hoja, dia, nombre) in enumerate(filas, start=1):
            entra = signo == "+"
            tk.Label(marco, text="Entra" if entra else "Sale", bg=TARJETA, fg=VERDE if entra else ROJO,
                     font=(FUENTE, 10, "bold"), anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 6), pady=2)
            for c, valor in enumerate((self.HOJAS[hoja], dia, nombre), start=1):
                tk.Label(marco, text=valor, bg=TARJETA, fg=TEXTO, font=(FUENTE, 10, "bold" if c == 3 else "normal"),
                         anchor="w").grid(row=r, column=c, sticky="w", padx=(0, 6), pady=2)

    def _conteo(self, marco, filas):
        for c, dia in enumerate([""] + NOMBRES_DIA):
            tk.Label(marco, text=dia, bg=TARJETA, fg=TENUE, font=(FUENTE, 9, "bold"), width=14, anchor="w" if c == 0 else "center").grid(row=0, column=c)
        for r, (hoja, numeros) in enumerate(filas, start=1):
            tk.Label(marco, text=self.HOJAS.get(hoja, hoja), bg=TARJETA, fg=TEXTO, font=(FUENTE, 10), width=14, anchor="w").grid(row=r, column=0, pady=3)
            for c, n in enumerate(numeros, start=1):
                tk.Label(marco, text=str(n), bg=TARJETA, fg=INDIGO_OSCURO, font=(FUENTE, 14, "bold"), width=8).grid(row=r, column=c)


class Lateral(tk.Frame):
    """Barra lateral índigo: ícono, nombre, menú, y abajo Salir y la versión (como Movimientos Docentes)."""

    def __init__(self, padre, app, secciones):
        super().__init__(padre, bg=INDIGO, width=230)
        self.pack_propagate(False)
        self.app, self.items = app, {}
        tk.Label(self, text="▤", bg=INDIGO, fg="white", font=(FUENTE, 30)).pack(anchor="w", padx=18, pady=(14, 0))
        tk.Label(self, text="Libro de firmas", bg=INDIGO, fg="white", font=(FUENTE, 15, "bold")).pack(anchor="w", padx=18)
        tk.Label(self, text="Escuela Hölters 4258 · ITH 4991", bg=INDIGO, fg="#D0D5EE", font=(FUENTE, 8)).pack(anchor="w", padx=18, pady=(0, 18))
        for clave, texto, icono in secciones:
            fila = tk.Label(self, text=f"{icono}   {texto}", bg=INDIGO, fg="white", font=(FUENTE, 11), anchor="w",
                            padx=14, pady=11, cursor="hand2")
            fila.pack(fill="x", padx=8, pady=2)
            fila.bind("<Button-1>", lambda _e, c=clave: app.mostrar(c))
            fila.bind("<Enter>", lambda _e, f=fila: f["bg"] != LATERAL_SEL and f.configure(bg=LATERAL_HOVER))
            fila.bind("<Leave>", lambda _e, f=fila: f["bg"] != LATERAL_SEL and f.configure(bg=INDIGO))
            self.items[clave] = fila
        tk.Label(self, text=f"Versión {VERSION}", bg=INDIGO, fg="#C5CAE9", font=(FUENTE, 8)).pack(side="bottom", anchor="w", padx=16, pady=(4, 12))
        for texto, accion in (("✕   Salir", app.destroy), ("🗁   Carpeta de salida", app.abrir_salida)):
            b = tk.Label(self, text=texto, bg=INDIGO, fg="white", font=(FUENTE, 11), anchor="w", padx=14, pady=9, cursor="hand2")
            b.pack(side="bottom", fill="x", padx=8)
            b.bind("<Button-1>", lambda _e, a=accion: a())
            b.bind("<Enter>", lambda _e, w=b: w.configure(bg=LATERAL_HOVER))
            b.bind("<Leave>", lambda _e, w=b: w.configure(bg=INDIGO))
        tk.Label(self, text="ABRIR", bg=INDIGO, fg="#C5CAE9", font=(FUENTE, 8, "bold")).pack(side="bottom", anchor="w", padx=16, pady=(0, 4))

    def marcar(self, clave):
        for k, fila in self.items.items():
            fila.configure(bg=LATERAL_SEL if k == clave else INDIGO, font=(FUENTE, 11, "bold" if k == clave else "normal"))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Libro de firmas docente – Hölters")
        icono = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "recursos", "app.ico")
        try:
            self.iconbitmap(icono)
        except tk.TclError:
            pass  # sin ícono la ventana funciona igual
        self.geometry("1180x780")
        self.minsize(1000, 700)
        aplicar_estilo(self)
        self.ruta_libro = None
        self.contenido = ttk.Frame(self)
        self.pantallas = {}
        secciones = [("armar", "Armar libro", "▤"), ("licencias", "Licencias", "✎"), ("manuales", "Horarios a mano", "◷"),
                    ("excluidos", "Excluidos", "⊘")]
        self.lateral = Lateral(self, self, secciones)
        self.lateral.pack(side="left", fill="y")
        self.contenido.pack(side="left", fill="both", expand=True)
        for clave, fabrica in (("armar", lambda: PantallaArmar(self.contenido, self)),
                               ("licencias", lambda: pantalla_licencias(self.contenido)),
                               ("manuales", lambda: pantalla_manuales(self.contenido)),
                               ("excluidos", lambda: pantalla_excluidos(self.contenido))):
            self.pantallas[clave] = fabrica()  # cada pantalla se arma una vez; cambiar de sección solo cambia cuál se ve
        self.mostrar("armar")
        if rutas.AVISO:
            self.after(300, self._problema_con_los_datos)

    def _problema_con_los_datos(self):
        """La carpeta compartida no abre desde esta PC: se muestra el motivo y se ofrece elegir la carpeta a mano."""
        if not messagebox.askyesno("Datos compartidos", rutas.AVISO + "\n\n¿Querés elegir la carpeta de datos a mano "
                                   "(por ejemplo, la unidad de red que usás en esta PC)?", parent=self):
            return
        carpeta = filedialog.askdirectory(parent=self, title="Elegí la carpeta \"Libro de firmas (datos)\"", mustexist=True)
        if not carpeta:
            return
        carpeta = os.path.normpath(carpeta)
        if not os.path.isfile(os.path.join(carpeta, "docentes.csv")):
            messagebox.showwarning("Carpeta equivocada", "Esa carpeta no tiene los datos (falta docentes.csv). "
                                   "Elegí la carpeta \"Libro de firmas (datos)\".", parent=self)
            return
        rutas.fijar_carpeta_datos(carpeta)
        messagebox.showinfo("Listo", "Se guardó la carpeta. El programa se abre de nuevo.", parent=self)
        subprocess.Popen([sys.executable] + ([] if getattr(sys, "frozen", False) else [os.path.join(BASE, "lanzador.py")]))
        self.destroy()

    def mostrar(self, clave):
        for p in self.pantallas.values():
            p.pack_forget()
        self.pantallas[clave].pack(fill="both", expand=True)
        self.lateral.marcar(clave)
        al_mostrar = getattr(self.pantallas[clave], "al_mostrar", None)
        if al_mostrar:
            al_mostrar()  # los datos son compartidos: se relee lo que cargó otra PC

    def abrir_salida(self):
        carpeta = os.path.dirname(self.ruta_libro) if self.ruta_libro else os.path.join(BASE, "salida")
        if os.path.isdir(carpeta):
            os.startfile(carpeta)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
