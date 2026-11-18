# Lista de preceptores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (en esta sesión, sin subagentes). Steps use checkbox syntax.

**Goal:** Armar e imprimir la hoja `prec. 2026` desde la app, con una pantalla Preceptores (días por persona y licencias).

**Architecture:** `preceptores.py` (lógica pura + CSV, sin pantalla) → `render_libro.py` (dibuja la hoja sobre el molde, que crece) → `libro_firmas.generar` (la agrega al libro) → `app.py` (pantalla y botón propio). Datos en `preceptores.csv` de la carpeta compartida.

**Tech Stack:** Python 3.13, openpyxl, tkinter, unittest (`.venv\Scripts\python.exe -X utf8 -W ignore -m unittest discover -s tests -t .`), Excel por COM solo para exportar a PDF y comprobar.

**Spec:** `docs/superpowers/specs/2026-11-18-preceptores-design.md`

## Global Constraints
- Repo público: tests con nombres inventados; nada de nombres reales ni de la ruta de red en código, docs ni tests. `datos/` está ignorado.
- Editar con Edit/Write, nunca con heredocs que lleven `\` o `\n` (se rompen).
- Versión 1.7.0 en `version.py` y `CHANGELOG.md`. Commit local, sin push.
- Hoja `prec. 2026`: bloques A–D (Lunes), E–H (Martes), I–L (Viernes), M–P (Miércoles) con el rótulo en la 2.ª columna de la fila 1; Jueves en I–L con el rótulo en J31 y renglones desde la fila 32. 23 renglones por bloque, 34,5 pt cada uno.
- Orden alfabético sin tildes (`clasificar.clave_docente`); apellido en mayúsculas; apóstrofo normal.
- Licencias de preceptores iguales a las de docentes y NUNCA en `licencias.csv`.

## Review Focus
- Persona sin ningún día tildado o repetida (mismo apellido y nombre): error claro al guardar.
- Licencia con "Hasta" anterior a "Desde", o con fechas escritas día/mes/año: se normaliza o se rechaza con mensaje.
- `preceptores.csv` inexistente o vacío: el libro de docentes se arma igual, sin la hoja.
- Un día con más de 23 personas: la hoja crece y Jueves baja sin pisarse.
- Apellido con apóstrofo o con espacios (`RÍOS DE LA VEGA`): se ordena y se imprime bien.

---

### Task 1: Datos y reglas (`preceptores.py`)
**Files:** Create `preceptores.py`, `tests/test_preceptores.py`.
**Interfaces — Produces:**
- `CAMPOS = ["apellido","nombre","cargo","dias","lic_desde","lic_hasta","lic_motivo","en_lista"]`
- `leer(ruta) -> list[dict]` (cadenas sin espacios sobrantes; `[]` si no existe) y `guardar(ruta, filas)` (valida todo antes de escribir; CSV `;`, UTF-8).
- `validar(fila) -> dict`: apellido y nombre obligatorios; `dias` normalizado a lista ordenada "lunes,martes,..." con al menos uno; fechas ISO (`repositorio.fecha_a_iso`); `desde <= hasta`; `en_lista` "si"/"no" (por defecto "si"). Lanza `ValueError` con mensaje legible.
- `estado(fila, hoy) -> str`: "" sin licencia; si no, `repositorio.estado_licencia`.
- `impreso(fila) -> str`: `"APELLIDO, Nombre"`.
- `listas_por_dia(filas, hoy) -> list[list[tuple[str,str]]]`: por día 0–4, `(impreso, cargo)` ordenado; una licencia vigente con `en_lista == "no"` saca a la persona.
- `licencias_vigentes(filas, hoy) -> list[dict]` para el informe.
- [ ] Tests (nombres inventados): `test_validar_exige_dia`, `test_validar_rechaza_desde_posterior`, `test_listas_por_dia_ordena_sin_tildes` (incluye `D'ALBA` y `RÍOS DE LA VEGA`), `test_licencia_vigente_no_saca_a_quien_sigue_en_lista`, `test_licencia_vigente_en_lista_no_la_saca_ni_vencida_ni_futura`, `test_guardar_rechaza_repetidos`, `test_leer_archivo_inexistente`.
- [ ] Ver fallar, implementar, ver pasar, commit.

### Task 2: Hoja `prec. 2026` que crece (`render_libro.py`)
**Files:** Modify `render_libro.py`; Create `tests/test_render_preceptores.py`.
**Interfaces — Produces:**
- `HOJA_PRECEPTORES = "prec. 2026"`, `DIAS_PRECEPTORES = (0, 2, 4, 1, 3)` (orden de la hoja: Lunes, Martes, Viernes, Miércoles, Jueves → índices de día).
- `render(plantilla, salida, listas, preceptores=None)`: si `preceptores` (lista por día de `(impreso, cargo)`) no es `None`, conserva y llena esa hoja.
- `render_solo_preceptores(plantilla, salida, preceptores)`: libro con solo esa hoja.
- Reglas: `N = max(23, máximo de los cuatro bloques superiores)`; cada uno lleva N renglones numerados (con o sin persona); Jueves arranca con su rótulo en la fila `N + 8` (J31 cuando N = 23) y lleva `max(23, nJueves)`; los renglones usados con borde medio en las tres columnas con datos y firma libre; filas de separación con las alturas del molde; los nombres largos se parten en dos líneas. Si no hay `preceptores`, se quita la hoja como hoy.
- [ ] Tests: con 22 personas coincide con el molde (valores y filas de Jueves); con 24 y con 50 el bloque superior llega a la fila 1+N, Jueves baja y no hay celdas pisadas; la hoja no aparece si `preceptores` es `None`; `leer_listas`/hojas de docentes siguen igual.
- [ ] Exportar a PDF con Excel (COM) el molde original y el generado con 22: misma cantidad de páginas; ver también 24 y 50. Fijar saltos de página manuales solo si hace falta.
- [ ] Commit.

### Task 3: Armado del libro (`libro_firmas.py`)
**Files:** Modify `libro_firmas.py`, `tests/` del pipeline si hace falta.
- [ ] Opción `--preceptores` (por defecto `rutas.en_datos("preceptores.csv")`, también en `opciones`); si el archivo existe, calcular `preceptores.listas_por_dia(filas, hoy)`, pasarlo a `render_libro.render` y agregar al informe una sección "Preceptores" (cantidad por día, licencias vigentes, avisos de licencia sin fin o vencida). Sin archivo, igual que hoy.
- [ ] `armar_preceptores(args) -> Resultado`-like simple (ruta del Excel) para el botón: usa `render_solo_preceptores`, salida `Lista de preceptores 2026.xlsx` en `salida`.
- [ ] Correr toda la suite y `libro_firmas.py` real con los PDF de `entrada\` (con una copia temporal del CSV): se genera y la hoja está.
- [ ] Commit.

### Task 4: Pantalla Preceptores (`app.py`)
**Files:** Modify `app.py`.
- [ ] `Formulario`: tipo de campo casillas de días (centinela `CASILLAS_DIAS` en lugar de la lista de opciones); su valor es el texto "lunes,martes,...".
- [ ] `pantalla_preceptores(padre, app)`: `TablaEditable` con columnas Nombre, Cargo, Días (`✔ ✔ ✔ ✔ ·`), Estado hoy; campos apellido, nombre, cargo (desplegable con los cargos existentes, admite otro), días, licencia desde/hasta/motivo, ¿Sigue en la lista?; mismas ayudas que Licencias; `al_mostrar = t.recargar`; botón "Armar lista de preceptores" que genera y abre en Excel; sección nueva "Preceptores" en el menú lateral.
- [ ] Probar con una ventana real sobre archivos temporales (agregar, editar, quitar, cambio desde otra PC) y abriendo la app completa.
- [ ] Commit.

### Task 5: Carga inicial, instalador y cierre
- [ ] Cargar `datos\preceptores.csv` desde la hoja actual (script de un solo uso en el scratchpad, no versionado): comprobar 22 personas con los cuatro días y las de Viernes (19), cargo más frecuente por persona, `^` → `'`.
- [ ] `instalador\LibroFirmas.iss`: agregar `preceptores.csv` a los datos iniciales; reconstruir con `publicar.ps1`.
- [ ] Versión 1.7.0, `CHANGELOG.md`, `ESTADO.md`, memoria; barrido de apellidos reales en todo el historial; `superpowers:verification-before-completion`; commit local (sin push).
