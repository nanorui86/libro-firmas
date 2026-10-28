"""Ventana del libro de firmas: elegir el horario, armar el libro y revisar los avisos antes de imprimir.

Tiene tres pestañas: Armar libro, Licencias y Horarios a mano. Toda la lógica vive en los otros módulos
(`libro_firmas.generar`, `repositorio`); acá solo hay pantalla.
"""
import json
import os
import queue
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

import libro_firmas
import maestro
import repositorio
from clasificar import DIAS

BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(BASE, "datos", "app_config.json")
RUTA_LICENCIAS = os.path.join(BASE, "datos", "licencias.csv")
RUTA_MANUALES = os.path.join(BASE, "datos", "horarios_manuales.csv")
RUTA_MAESTRO = os.path.join(BASE, "datos", "docentes.csv")

# Paleta del propio libro: papel, tinta, verde de las franjas del Excel, lápiz.
PAPEL, TINTA, VERDE, FRANJA, LAPIZ, SELLO, AMBAR = "#F4EFE3", "#2A2823", "#476A3C", "#C5D9A0", "#8B8576", "#A23B2C", "#B27B16"
PAUTA = "#B9CDA0"
SERIF, SANS = "Georgia", "Segoe UI"
NOMBRES_DIA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

COMO_IMPRIMIR = """\
1. Tocá "Abrir en Excel para imprimir". Se abre el libro recién armado.

2. En Excel: Archivo > Imprimir. En la lista de qué imprimir elegí "Imprimir todo el libro" (así salen las dos \
hojas: mañana y mañana y tarde).

3. Dejá la escala en 100 % ("Sin escala"; no uses "Ajustar a una página") y el papel en A4 vertical. Los \
renglones miden lo mismo que los del libro de papel y por eso no se achica nada.

4. Cada hoja sale en varias páginas: una con Lunes y Martes, otra con Miércoles y Jueves, otra con Viernes, y los \
renglones del 24 en adelante en la página siguiente. Cada página cae sobre una tira del libro.

5. La primera vez imprimí una sola página y apoyala sobre el libro de papel, a contraluz, para ver que los \
renglones coinciden. Si coinciden, ya podés imprimir todo.

Las firmas se hacen en el libro de papel, no en esta hoja."""


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
    raiz.configure(bg=PAPEL)
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure(".", background=PAPEL, foreground=TINTA, font=(SANS, 10), bordercolor=PAUTA, lightcolor=PAPEL, darkcolor=PAPEL)
    s.configure("TFrame", background=PAPEL)
    s.configure("TLabel", background=PAPEL, foreground=TINTA)
    s.configure("Lapiz.TLabel", foreground=LAPIZ)
    s.configure("Titulo.TLabel", font=(SERIF, 20, "bold"), background=FRANJA, foreground=TINTA)
    s.configure("Sub.TLabel", background=FRANJA, foreground="#3B4A33")
    s.configure("Seccion.TLabel", font=(SERIF, 13, "bold"))
    s.configure("TNotebook", background=PAPEL, borderwidth=0)
    s.configure("TNotebook.Tab", background=PAPEL, padding=(16, 7), font=(SANS, 10), borderwidth=0)
    s.map("TNotebook.Tab", background=[("selected", "#FBF8F0")], foreground=[("selected", VERDE)],
          font=[("selected", (SANS, 10, "bold"))])
    s.configure("TButton", padding=(12, 6), background="#E8E1CF", foreground=TINTA, borderwidth=1)
    s.map("TButton", background=[("active", "#DDD5BF"), ("disabled", PAPEL)], foreground=[("disabled", LAPIZ)])
    s.configure("Grande.TButton", font=(SANS, 12, "bold"), padding=(22, 10), background=VERDE, foreground="#FFFFFF")
    s.map("Grande.TButton", background=[("active", "#3A5831"), ("disabled", "#A9B79F")], foreground=[("disabled", "#FFFFFF")])
    s.configure("TEntry", fieldbackground="#FFFFFF", padding=4)
    s.configure("TCombobox", fieldbackground="#FFFFFF", padding=4)
    s.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", rowheight=26, bordercolor=PAUTA)
    s.configure("Treeview.Heading", background=FRANJA, foreground=TINTA, font=(SANS, 10, "bold"), padding=5)
    s.map("Treeview", background=[("selected", VERDE)], foreground=[("selected", "#FFFFFF")])
    s.configure("Horizontal.TProgressbar", background=VERDE, troughcolor="#E8E1CF")


# ---------- tabla editable genérica ----------

class Formulario(tk.Toplevel):
    """Ventana modal con un campo por columna. `campos`: [(clave, etiqueta, valores_del_desplegable | None)]."""

    def __init__(self, padre, titulo, campos, valores, ayuda="", validar=None):
        super().__init__(padre)
        self.title(titulo)
        self.configure(bg=PAPEL, padx=20, pady=16)
        self.resizable(False, False)
        self.transient(padre.winfo_toplevel())
        self.resultado, self._validar, self._vars = None, validar, {}
        ttk.Label(self, text=titulo, style="Seccion.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        for i, (clave, etiqueta, opciones) in enumerate(campos, start=1):
            ttk.Label(self, text=etiqueta).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=4)
            var = self._vars[clave] = tk.StringVar(value=valores.get(clave, ""))
            if opciones is None:
                widget = ttk.Entry(self, textvariable=var, width=34)
            else:
                widget = ttk.Combobox(self, textvariable=var, values=opciones, width=32)
            widget.grid(row=i, column=1, sticky="ew", pady=4)
            if i == 1:
                widget.focus_set()
        fila = len(campos) + 1
        if ayuda:
            ttk.Label(self, text=ayuda, style="Lapiz.TLabel", wraplength=380, justify="left").grid(
                row=fila, column=0, columnspan=2, sticky="w", pady=(6, 0))
            fila += 1
        self._error = ttk.Label(self, text="", foreground=SELLO, wraplength=380, justify="left")
        self._error.grid(row=fila, column=0, columnspan=2, sticky="w", pady=(6, 0))
        botones = ttk.Frame(self)
        botones.grid(row=fila + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(botones, text="Guardar", command=self._aceptar).pack(side="right")
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

    def __init__(self, padre, columnas, campos, leer, guardar, ayuda="", opciones=None, validar=None, vista=None):
        """columnas: [(clave, título, ancho)]; campos: ver Formulario; leer() -> filas; guardar(filas);
        vista(fila) -> dict con lo que se muestra (por defecto, la fila misma)."""
        super().__init__(padre)
        self.columnas, self.campos, self.leer, self.guardar = columnas, campos, leer, guardar
        self.opciones = opciones or (lambda: {})
        self.validar, self.vista = validar, vista or (lambda f: f)
        self.filas = []
        if ayuda:
            ttk.Label(self, text=ayuda, style="Lapiz.TLabel", wraplength=760, justify="left").pack(anchor="w", pady=(0, 8))
        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        self.arbol = ttk.Treeview(cuerpo, columns=[c[0] for c in columnas], show="headings", selectmode="browse")
        for clave, titulo, ancho in columnas:
            self.arbol.heading(clave, text=titulo)
            self.arbol.column(clave, width=ancho, anchor="w")
        barra = ttk.Scrollbar(cuerpo, orient="vertical", command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.arbol.bind("<Double-1>", lambda _e: self.editar())
        self.arbol.tag_configure("par", background="#FBF8F0")
        self.arbol.tag_configure("apagada", foreground=LAPIZ)
        botones = ttk.Frame(self)
        botones.pack(fill="x", pady=(10, 0))
        ttk.Button(botones, text="Agregar", command=self.agregar).pack(side="left")
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
            tags = ("par",) if i % 2 else ()
            if v.get("_apagada"):
                tags += ("apagada",)
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
        f = Formulario(self, titulo, campos, valores, ayuda=self.ayuda_formulario, validar=self.validar)
        return f.resultado

    ayuda_formulario = ""

    def _guardar_con(self, nuevas):
        try:
            self.guardar(nuevas)
        except (ValueError, OSError) as e:
            messagebox.showerror("No se guardó", str(e), parent=self)
            return False
        self.recargar()
        return True

    def agregar(self):
        nueva = self._formulario("Agregar", {})
        if nueva:
            self._guardar_con(self.filas + [nueva])

    def editar(self):
        i = self._seleccion()
        if i is None:
            return
        nueva = self._formulario("Editar", self.vista_para_editar(self.filas[i]))
        if nueva:
            self._guardar_con(self.filas[:i] + [nueva] + self.filas[i + 1:])

    vista_para_editar = staticmethod(lambda fila: fila)

    def quitar(self):
        i = self._seleccion()
        if i is None:
            return
        if messagebox.askyesno("Quitar", "¿Quitar esta fila de la lista?", parent=self):
            self._guardar_con(self.filas[:i] + self.filas[i + 1:])


def tabla_licencias(padre):
    hoy = date.today()
    campos = [("docente", "Docente", None), ("desde", "Desde", None), ("hasta", "Hasta", None),
              ("motivo", "Motivo", None), ("en_lista", "¿Sigue en la lista?", None)]

    def vista(f):
        en_lista = "Sí" if f["en_lista"] != "no" else "No"
        estado = repositorio.estado_licencia(f, hoy)
        return {"docente": f["docente"], "desde": repositorio.iso_a_fecha(f["desde"]), "hasta": repositorio.iso_a_fecha(f["hasta"]),
                "motivo": f["motivo"], "en_lista": en_lista, "estado": estado, "_apagada": estado == "Vencida"}

    def validar(v):
        return repositorio.validar_licencia(dict(v, en_lista="no" if v["en_lista"].lower().startswith("n") else "si"))

    def para_editar(f):
        return dict(f, desde=repositorio.iso_a_fecha(f["desde"]), hasta=repositorio.iso_a_fecha(f["hasta"]),
                    en_lista="Sí" if f["en_lista"] != "no" else "No")

    t = TablaEditable(
        padre,
        columnas=[("docente", "Docente", 210), ("desde", "Desde", 90), ("hasta", "Hasta", 90), ("motivo", "Motivo", 190),
                  ("en_lista", "¿Sigue en la lista?", 140), ("estado", "Estado hoy", 150)],
        campos=campos,
        leer=lambda: repositorio.leer_licencias(RUTA_LICENCIAS),
        guardar=lambda filas: repositorio.guardar_licencias(RUTA_LICENCIAS, filas),
        ayuda=("Mientras una licencia esté vigente, el docente sigue en la lista, en los mismos días y turnos de siempre, "
               "aunque el horario nuevo ya no lo traiga. Si ponés \"No\" en ¿Sigue en la lista?, sale del libro. "
               "Las fechas van como día/mes/año; \"Hasta\" puede quedar vacío si todavía no se sabe."),
        opciones=lambda: {"docente": repositorio.nombres_docentes(RUTA_MAESTRO), "motivo": repositorio.MOTIVOS,
                          "en_lista": ["Sí", "No"]},
        validar=validar, vista=vista)
    t.vista_para_editar = para_editar
    t.ayuda_formulario = "Podés escribir el nombre si no está en la lista, como Apellido, Nombre."
    return t


def tabla_manuales(padre):
    def vista(f):
        try:
            turno = repositorio.turno_de(f["modulos"])
        except ValueError:
            turno = "revisar"
        return {"docente": f["docente"], "dia": f["dia"].capitalize(), "modulos": f["modulos"], "turno": turno}

    t = TablaEditable(
        padre,
        columnas=[("docente", "Docente", 240), ("dia", "Día", 110), ("modulos", "Módulos", 140), ("turno", "Turno", 140)],
        campos=[("docente", "Docente", None), ("dia", "Día", None), ("modulos", "Módulos", None)],
        leer=lambda: repositorio.leer_manuales(RUTA_MANUALES),
        guardar=lambda filas: repositorio.guardar_manuales(RUTA_MANUALES, filas),
        ayuda=("Para los docentes cuyo horario viene en un PDF escaneado o en una foto (hoy, los de inglés): una fila por "
               "docente y día. Cuando ese horario cambie hay que cargarlo de nuevo."),
        opciones=lambda: {"docente": repositorio.nombres_docentes(RUTA_MAESTRO),
                          "dia": [d.capitalize() for d in NOMBRES_DIA_SIN_TILDE]},
        validar=repositorio.validar_manual, vista=vista)
    t.ayuda_formulario = ("Módulos: un rango o una lista, por ejemplo 1-6 o 1-4,8-9. Del 1 al 7 es la mañana (hasta las "
                          "13:05) y del 8 al 13 la tarde. Con cualquier módulo de la tarde, ese día va en la hoja de "
                          "mañana y tarde.")
    t.vista_para_editar = lambda f: dict(f, dia=f["dia"].capitalize())
    return t


NOMBRES_DIA_SIN_TILDE = list(DIAS)


# ---------- resultado en renglones pautados ----------

class Renglones(tk.Canvas):
    """Docentes por día en cada hoja, dibujados como renglones de libro."""

    def __init__(self, padre):
        super().__init__(padre, height=150, bg="#FBF8F0", highlightthickness=1, highlightbackground=PAUTA)
        self.bind("<Configure>", lambda _e: self.dibujar())
        self.conteo = None

    def mostrar(self, conteo):
        self.conteo = conteo
        self.dibujar()

    def dibujar(self):
        self.delete("all")
        w = max(self.winfo_width(), 400)
        izq, ancho_col = 150, (w - 150 - 12) / 5
        for y in (44, 88, 132):
            self.create_line(10, y, w - 10, y, fill=PAUTA)
        for i, dia in enumerate(NOMBRES_DIA):
            self.create_text(izq + ancho_col * (i + 0.5), 24, text=dia, font=(SANS, 10, "bold"), fill=VERDE)
        for fila, (clave, etiqueta) in enumerate((("tm", "Hoja mañana"), ("tmyt", "Hoja mañana y tarde"))):
            y = 66 + 44 * fila
            self.create_text(14, y, text=etiqueta, anchor="w", font=(SANS, 10), fill=TINTA)
            for i in range(5):
                n = self.conteo[clave][i] if self.conteo else "–"
                self.create_text(izq + ancho_col * (i + 0.5), y, text=str(n), font=(SERIF, 20, "bold"), fill=TINTA)


# ---------- pestaña principal ----------

class PestanaArmar(ttk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, padding=(4, 14, 4, 4))
        self.app, self.cola, self.ruta_libro = app, queue.Queue(), None
        config = leer_config()
        self.var_prof = tk.StringVar(value=config.get("profesores", ""))
        self.var_cursos = tk.StringVar(value=config.get("cursos", ""))
        self.columnconfigure(1, weight=1)
        self._selector(0, "Horario de profesores (PDF de Untis)", self.var_prof)
        self._selector(1, "Horario de cursos (PDF, para controlar)", self.var_cursos, opcional=True)

        acciones = ttk.Frame(self)
        acciones.grid(row=2, column=0, columnspan=3, sticky="w", pady=(16, 8))
        self.boton = ttk.Button(acciones, text="Armar libro", style="Grande.TButton", command=self.armar)
        self.boton.pack(side="left")
        self.estado = ttk.Label(acciones, text="", style="Lapiz.TLabel")
        self.estado.pack(side="left", padx=16)
        self.barra = ttk.Progressbar(acciones, mode="indeterminate", length=140)

        self.renglones = Renglones(self)
        self.renglones.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        self.renglones.mostrar(None)

        ttk.Label(self, text="Para revisar antes de imprimir", style="Seccion.TLabel").grid(row=4, column=0, columnspan=3, sticky="w")
        marco = ttk.Frame(self)
        marco.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(6, 10))
        self.rowconfigure(5, weight=1)
        self.avisos = tk.Text(marco, height=8, wrap="word", bg="#FFFFFF", fg=TINTA, relief="flat", font=(SANS, 10),
                              padx=10, pady=8, state="disabled", highlightthickness=1, highlightbackground=PAUTA)
        barra = ttk.Scrollbar(marco, command=self.avisos.yview)
        self.avisos.configure(yscrollcommand=barra.set)
        self.avisos.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.avisos.tag_configure("error", foreground=SELLO, font=(SANS, 10, "bold"))
        self.avisos.tag_configure("aviso", foreground=AMBAR)
        self.avisos.tag_configure("info", foreground=LAPIZ)
        self.avisos.tag_configure("ok", foreground=VERDE, font=(SANS, 10, "bold"))
        self._escribir_avisos([("info", "Elegí el PDF de profesores y tocá \"Armar libro\". Acá aparece lo que conviene mirar antes de imprimir.")])

        pie = ttk.Frame(self)
        pie.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.b_excel = ttk.Button(pie, text="Abrir en Excel para imprimir", command=self.abrir_libro, state="disabled")
        self.b_excel.pack(side="left")
        self.b_carpeta = ttk.Button(pie, text="Abrir carpeta", command=self.abrir_carpeta, state="disabled")
        self.b_carpeta.pack(side="left", padx=8)
        self.b_informe = ttk.Button(pie, text="Ver informe completo", command=self.ver_informe, state="disabled")
        self.b_informe.pack(side="left")
        ttk.Button(pie, text="Cómo imprimir", command=self.como_imprimir).pack(side="right")
        self.informe = ""

    def _selector(self, fila, etiqueta, var, opcional=False):
        ttk.Label(self, text=etiqueta).grid(row=fila, column=0, sticky="w", pady=4, padx=(0, 12))
        ttk.Entry(self, textvariable=var).grid(row=fila, column=1, sticky="ew", pady=4)
        botones = ttk.Frame(self)
        botones.grid(row=fila, column=2, padx=(8, 0))
        ttk.Button(botones, text="Elegir…", command=lambda: self._elegir(var)).pack(side="left")
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
        marca = {"error": "✖  ", "aviso": "!  ", "info": "·  ", "ok": "✔  "}
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
            messagebox.showwarning("No encuentro el PDF de cursos", "Elegí otro PDF de cursos o tocá Borrar para armar sin él.", parent=self)
            return
        guardar_config({"profesores": profesores, "cursos": cursos})
        self.boton.configure(state="disabled")
        for b in (self.b_excel, self.b_carpeta, self.b_informe):
            b.configure(state="disabled")
        self.estado.configure(text="Armando el libro… tarda unos 20 segundos.")
        self.barra.pack(side="left")
        self.barra.start(12)
        args = libro_firmas.opciones(profesores, base=BASE, cursos=cursos or None)
        threading.Thread(target=self._trabajo, args=(args,), daemon=True).start()
        self.after(150, self._esperar)

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
        self.barra.stop()
        self.barra.pack_forget()
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
            self._escribir_avisos([("error", p) for p in r.problemas] or [("error", "No se pudo armar el libro. Mirá el informe completo.")])
            return
        self.ruta_libro = r.ruta_libro
        self.b_excel.configure(state="normal")
        self.b_carpeta.configure(state="normal")
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
        ventana = tk.Toplevel(self)
        ventana.title("Informe completo")
        ventana.configure(bg=PAPEL)
        ventana.geometry("820x560")
        texto = tk.Text(ventana, wrap="word", bg="#FFFFFF", fg=TINTA, font=("Consolas", 10), padx=12, pady=10, relief="flat")
        barra = ttk.Scrollbar(ventana, command=texto.yview)
        texto.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        texto.pack(fill="both", expand=True)
        texto.insert("1.0", self.informe)
        texto.configure(state="disabled")

    def como_imprimir(self):
        ventana = tk.Toplevel(self)
        ventana.title("Cómo imprimir")
        ventana.configure(bg=PAPEL, padx=24, pady=20)
        ventana.transient(self.winfo_toplevel())
        ttk.Label(ventana, text="Cómo imprimir el libro", style="Seccion.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(ventana, text=COMO_IMPRIMIR, wraplength=520, justify="left").pack(anchor="w")
        ttk.Button(ventana, text="Entendido", command=ventana.destroy).pack(anchor="e", pady=(16, 0))


# ---------- ventana ----------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Libro de firmas docente")
        self.geometry("920x740")
        self.minsize(820, 640)
        aplicar_estilo(self)
        cab = tk.Frame(self, bg=FRANJA, padx=22, pady=14)
        cab.pack(fill="x")
        ttk.Label(cab, text="Libro de firmas docente", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(cab, text="Arma las listas de mañana y de mañana y tarde a partir del horario de Untis.", style="Sub.TLabel").pack(anchor="w")
        tk.Frame(self, bg=VERDE, height=3).pack(fill="x")
        libro = ttk.Notebook(self)
        libro.pack(fill="both", expand=True, padx=18, pady=(10, 14))
        libro.add(PestanaArmar(libro, self), text="Armar libro")
        libro.add(ttk.Frame(libro, padding=(4, 14, 4, 4)), text="Licencias")
        libro.add(ttk.Frame(libro, padding=(4, 14, 4, 4)), text="Horarios a mano")
        for marco, fabrica in zip(libro.winfo_children()[1:], (tabla_licencias, tabla_manuales)):
            fabrica(marco).pack(fill="both", expand=True)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
