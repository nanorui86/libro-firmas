# Libro de firmas docente: estado

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
- Completar `desde`/`hasta` de las licencias (hoy "sin fecha de fin"; el informe lo recuerda).
- Prueba física: imprimir una hoja y apoyarla sobre el libro real.
- Subir los últimos cambios a GitHub cuando el usuario lo autorice (github.com/nanorui86/libro-firmas).

**Entorno**
- `pdfplumber` global estaba roto (falta `charset_normalizer`): se usa `.venv\` del proyecto (pdfplumber + openpyxl). Sin
  `pytest`: tests con `unittest`.
- Commits con el correo `noreply` de GitHub (config local): la cuenta bloquea pushes que exponen el personal.
- Al insertar texto con `\n` desde heredocs de shell se rompieron strings dos veces: editar con la herramienta de edición.
