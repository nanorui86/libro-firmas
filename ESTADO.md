# Libro de firmas docente: estado

## 2026-10-29: informe completo legible
- "Ver informe completo" ahora es una ventana con tarjetas (`VentanaInforme` en `app.py`) armada por `informe_vista.py`, que
  interpreta el texto de `informe.txt`: título + resumen en una etiqueta, "Qué hacer", docentes en negrita, celdas sin curso como
  "Mar mód. 3-4", cambios como tabla Entra/Sale con hoja y día, conteo como tabla. `informe.txt` sigue siendo texto plano.
- Excepciones y licencias se escriben en el informe en una línea por docente, sin repetir.

## 2026-10-28 (noche): ajustes tras probar la app
- Nombres: una inicial ("A.") ahora encaja con el nombre que empieza así, y la comparación de "figuraba en el libro anterior" usa
  también el nombre tal como se imprime. Un docente cuyo nombre en Untis difiere del del libro (nombre compuesto) se arregla
  corrigiendo la columna `impreso` de `datos/docentes.csv` (ahí se edita a mano).
- Nueva pantalla **Excluidos** (filas `quitar` de `datos/excepciones.csv`, todos los días y sin fecha de fin): docentes que figuran
  en Untis pero no van en el libro; el programa deja de avisar por ellos.
- El informe completo explica cada sección con "Qué hacer" (las diferencias contra el libro son solo para controlar).
- El armado muestra un contador de segundos en lugar de la barra.

## 2026-10-28 (tarde): app de escritorio
El usuario pidió una app para crear el listado sin pelearse con la línea de comandos ni con la impresión. Hecha con tkinter
(stdlib): `app.py` + lanzador `Libro de firmas.pyw` + acceso directo en el Escritorio (`pythonw.exe` del `.venv`).
- Pestañas: Armar libro (elige PDFs, arma en un hilo, conteos por día como renglones pautados, avisos, abrir en Excel,
  informe, "Cómo imprimir"), Licencias y Horarios a mano (tablas editables que guardan al instante).
- `libro_firmas.generar` ahora devuelve un `Resultado` (ok, informe, ruta, sin_tratamiento, problemas, conteo, avisos); `main` solo imprime.
- Nuevo: `repositorio.py` (fechas dd/mm/aaaa <-> ISO, validación, estado de licencia) y `maestro.fijar_tratamiento`
  (la ventana pregunta Profesor/Profesora cuando falta). 57 tests.
- Diseño: el usuario no quiso la primera versión (verde/papel) y pidió el formato de Movimientos Docentes y Registro de Egresados:
  barra lateral índigo (#3F51B5) con menú, fondo gris claro, tarjetas blancas, etiquetas de sección en mayúsculas, botones
  contorneados y franja ámbar de aviso. Sigue siendo tkinter (imita Material; esas apps son WPF).
- Probado con el horario real: 18 s, mismos conteos que antes (tm 25/22/19/20/30, tmyt 29/24/35/29/17).
- Decisión: NO hay botón de impresión automática hasta la prueba física (se explica cómo imprimir y se abre Excel).
- Dos docentes figuran con otro nombre en el libro anterior (ortografía distinta); la ventana lo avisa como "puede estar
  escrito distinto".

## 2026-10-28
**Funciona de punta a punta** con el horario real del 16/10/2026: `libro_firmas.py` lee el PDF de Untis (66 docentes), suma
los horarios de inglés transcriptos a mano, valida contra el PDF de cursos, asigna turno por docente y día, aplica excepciones
y licencias y llena el molde de Excel. 40 tests (`python -m unittest discover -s tests -t .`).

**Decisiones**
- Módulos 1-7 = mañana, 8-13 = tarde. Cualquier módulo 8-13 ese día manda al docente a la hoja `tmyt`.
- Celdas "Cargo" y "PLANIFICACIÓN" cuentan como presencia.
- Salida en `.xlsx`, con solo las dos hojas del libro. Nunca se escribe sobre el original.
- La impresión NO es "1 página": zoom 100 y renglones de 34/35 pt (el renglón del libro físico). Saltos de página fijos
  (columnas tras H y P, y V en `tm`; filas de a 24). La primera página lleva siempre sus 23 renglones numerados; los nombres
  largos se parten en dos líneas.
- Tratamiento (Profesor/a): del `.mdb` (columna `CARGO`; su columna `Tratamiento` trae el nombre), luego el libro actual; si
  ninguno, se frena. No se adivina.
- **Licencias** (`datos/licencias.csv`: docente; desde; hasta; motivo; en_lista): el docente **sigue en la lista** mientras
  dura la licencia, en los turnos de siempre, aunque el horario nuevo ya no lo traiga; solo sale con `en_lista = no`. No se
  imprime leyenda (la leyenda va en el libro físico, donde firman). El `.csv` es el registro. Si la licencia vence y el docente
  no tiene clases, el informe avisa que ya no figura. Los turnos de siempre salen de `datos/turnos_ultimo_libro.csv` (se
  reescribe en cada corrida) y, la primera vez, del libro actual.
- `datos/excepciones.csv` queda para agregar/quitar a mano (hoy: el ayudante de laboratorio, que va solo en `prec. 2026`).
- Horario de inglés: ESCANEO sin texto, no se lee por coordenadas; se transcribe a `datos/horarios_manuales.csv`. Hay que
  repetirlo cada vez que cambie. Las hojas dicen "2025" pero es el de 2026 (confirmado por el usuario).
- Repo público: sin datos personales. `datos/`, `entrada/`, `salida/`, PDFs, Excel y `.mdb` están en `.gitignore`. Tests con
  nombres inventados. Barrer nombres reales (también el historial) antes de cada push.

**Hallazgos sobre los datos**
- El PDF de profesores puede estar incompleto: una docente con 15 módulos en el de cursos no tenía página;
  `validar.docentes_solo_en_cursos` la reconstruye desde cursos y lo avisa.
- Cuatro docentes figuran de licencia (una por maternidad) y no tienen horario en Untis: cargados en `licencias.csv`.
- Las "horas" de la cabecera pueden superar los módulos (clases simultáneas u horas fuera de grilla): aviso, no error.

**Pendiente**
- **Para el 2026-10-29 (pedido del usuario):** (1) revisar el formato de salida del Excel: "hay cosas que no se ven bien" (sin detallar;
  pedirle que muestre cuáles: mirar el `.xlsx` generado y su vista de impresión); (2) volver a poner una barra de progreso junto al
  contador de segundos al armar el libro (el usuario primero pidió contador en vez de barra, ahora quiere las dos; la barra puede ser
  determinada según el tiempo estimado de ~18 s).
- Que el usuario pruebe la app (doble clic en el acceso directo) y diga qué le falta.
- Completar `desde`/`hasta` de las licencias (hoy "sin fecha de fin"; el informe lo recuerda).
- Prueba física: imprimir una hoja y apoyarla sobre el libro real.
- Subir los últimos cambios a GitHub cuando el usuario lo autorice (github.com/nanorui86/libro-firmas).

**Entorno**
- `pdfplumber` global estaba roto (falta `charset_normalizer`): se usa `.venv\` del proyecto (pdfplumber + openpyxl). Sin
  `pytest`: tests con `unittest`.
- Commits con el correo `noreply` de GitHub (config local): la cuenta bloquea pushes que exponen el personal.
- Al insertar texto con `\n` desde heredocs de shell se rompieron strings dos veces: editar con la herramienta de edición.
