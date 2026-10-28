# Libro de firmas docente: estado

## 2026-10-28
**Funciona de punta a punta** con el horario real del 16/10/2026 (66 páginas de docentes):
`libro_firmas.py` lee el PDF de Untis, valida contra el PDF de cursos, asigna turno por docente y día,
aplica excepciones y llena el molde de Excel. 26 tests (`python -m unittest discover -s tests -t .`).

**Decisiones**
- Módulos 1-7 = mañana, 8-13 = tarde. Cualquier módulo 8-13 ese día manda al docente a la hoja `tmyt`.
- Celdas "Cargo" cuentan como presencia (confirmado por el usuario).
- Salida en `.xlsx`, con solo las dos hojas del libro. Nunca se escribe sobre el original.
- La impresión NO es "1 página": zoom 100 y renglones de 34/35 pt (el renglón del libro físico). Los saltos
  de página se fijan a mano (columnas tras H y P, y V en `tm`; filas de a 24). No se escala nada.
- La primera página lleva siempre sus 23 renglones numerados, como el original. Los nombres largos se parten
  en dos líneas (antes se cortaban al imprimir).
- Tratamiento (Profesor/a): del `.mdb` (columna `CARGO`; ojo, su columna `Tratamiento` trae el nombre). Si el `.mdb`
  no lo resuelve, se usa el libro actual. Si ninguno, **se frena** y se pide completarlo: no se adivina.
- Licencias y suplentes: `datos/excepciones.csv` (con desde/hasta; el informe avisa las vencidas y las sin fin).
- Repo público: sin datos personales. `datos/`, `entrada/`, `salida/`, PDFs, Excel y `.mdb` están en `.gitignore`.
  Los tests usan nombres inventados. Barrer nombres reales antes de cada push.

**Hallazgos sobre los datos (para el usuario)**
- El PDF de profesores está incompleto: una docente con 15 módulos en el PDF de cursos no tiene página.
  `validar.docentes_solo_en_cursos` la reconstruye desde cursos y lo avisa en el informe.
- Diez docentes del libro actual no tienen clases en ningún PDF (probable baja o licencia sin cargar).
- Las "horas" de la cabecera pueden superar los módulos (clases simultáneas u horas fuera de grilla): es aviso, no error.

**Pendiente**
- **Horario de inglés: cargado** (`entrada\Horarios profs ingles.pdf`, 8 páginas). Es un ESCANEO con diseños distintos,
  sin texto: no se lee por coordenadas. Se transcribió a mano a `datos\horarios_manuales.csv` (ocho docentes) y el resultado
  coincide día por día con el libro actual. Cada hoja dice "Horario INGLÉS 2025": confirmar que está vigente.
  Las celdas "PLANIFICACIÓN" (viernes, módulo 7) se cuentan como presencia; no cambió ningún resultado.
- **Faltan dos docentes del libro actual que no están en ningún horario:** uno en licencia y otra que no figura en el PDF de
  Untis ni en el de inglés (confirmar con el usuario).
- **Licencias:** los docentes de licencia no firman pero el libro lleva la leyenda "licencia". Falta definir dónde se imprime
  la leyenda (celda de tratamiento / junto al nombre) y cargar a los de licencia como excepciones con esa leyenda.
- Completar `hasta` y `motivo` de las excepciones sembradas (dos docentes de licencia/suplente).
- Prueba física: imprimir una hoja y apoyarla sobre el libro real.
- Backup público: github.com/nanorui86/libro-firmas. Los cambios nuevos se suben cuando el usuario lo autorice.

**Resuelto con el usuario (2026-10-28)**
- El ayudante de laboratorio aparece en el PDF por reemplazos, pero va solo en `prec. 2026`: excluido del libro de docentes
  con una excepción `quitar` permanente (no se le exige tratamiento a quien no va en el libro).
- Tratamientos confirmados: los tres que discrepaban entre `.mdb` y libro son Profesora (el `.mdb` tenía mal uno).

**Entorno**
- `pdfplumber` global estaba roto (falta `charset_normalizer`): se usa `.venv\` del proyecto (pdfplumber + openpyxl). No hay `pytest`: tests con `unittest`.
- Commits de este repo con el correo `noreply` de GitHub (config local), porque la cuenta bloquea pushes que exponen el correo personal.
- `salida/Lib. Firmas 2026 (horario 2026-10-16).xlsx` es de PRUEBA: ya NO es de prueba respecto de tratamientos, pero está incompleto hasta cargar el horario de inglés.
