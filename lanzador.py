"""Punto de entrada del programa: abre la ventana. Con --cli arma el libro desde la línea de comandos
(`Libro de firmas.exe --cli "Profesores.pdf" --cursos "Cursos.pdf"`), útil para probar la instalación."""
import os
import sys
import traceback

BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


def main():
    os.chdir(BASE)
    if BASE not in sys.path:
        sys.path.insert(0, BASE)
    try:
        if "--cli" in sys.argv:
            if sys.stdout is None:  # empaquetado sin consola
                sys.stdout = open(os.devnull, "w", encoding="utf-8")
            import libro_firmas
            argv = [a for a in sys.argv[1:] if a != "--cli"]
            sys.exit(libro_firmas.main(argv))
        import app
        app.main()
    except SystemExit:
        raise
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


if __name__ == "__main__":
    main()
