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
- Tratamiento de un docente sin dato en ninguna fuente (ayudante en el `.mdb`).
- Tres discrepancias de género entre el `.mdb` y el libro actual (el informe las lista).
- Completar `hasta` y `motivo` de las excepciones sembradas.
- Prueba física: imprimir una hoja y apoyarla sobre el libro real.
- Backup público en GitHub (cuenta del usuario), previo barrido de nombres.
