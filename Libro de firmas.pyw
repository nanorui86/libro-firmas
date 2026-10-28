"""Lanzador: doble clic para abrir la ventana del libro de firmas (sin consola)."""
import os
import sys
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.path.insert(0, BASE)

try:
    import app
    app.main()
except Exception:
    # Sin consola no se vería el error: se guarda y se muestra.
    texto = traceback.format_exc()
    with open(os.path.join(BASE, "error_app.txt"), "w", encoding="utf-8") as f:
        f.write(texto)
    import tkinter
    from tkinter import messagebox
    raiz = tkinter.Tk()
    raiz.withdraw()
    messagebox.showerror("Libro de firmas", "No se pudo abrir el programa.\n\n" + texto[-900:])
