# libro-firmas

Arma automáticamente las listas del **libro de firmas docente** (las hojas que se imprimen y se pegan en el libro
de asistencia) a partir del horario de docentes que exporta **Untis** en PDF.

Cada docente aparece, **día por día**, en una de dos hojas:

| Hoja | Quién | Regla |
|---|---|---|
| `tm` (turno mañana) | clases solo en los módulos 1 a 7 (hasta las 13:05) | |
| `tmyt` (mañana y tarde) | al menos un módulo 8 a 13 ese día (hasta las 18:05) | aunque no tenga nada a la mañana |

Un mismo docente puede estar en `tm` un día y en `tmyt` otro.

## Cómo funciona

1. `parse_horario.py` lee el PDF por **coordenadas** (`pdfplumber`): una celda está ocupada si tiene texto o su
   rectángulo propio. Nombre y horas de la cabecera se separan por tamaño de fuente, porque el celular queda
   pegado a las horas en el texto plano.
2. `validar.py` cruza con el PDF de cursos. Detecta docentes del horario que figuran en cursos sin clase, y
   docentes que el export de Untis dejó **sin página** (los reconstruye desde cursos y lo avisa).
3. `clasificar.py` aplica la regla de turno. `licencias.py` maneja las licencias: el docente **sigue en la lista**
   mientras dura la licencia (con `desde`, `hasta` y motivo), aunque el horario nuevo ya no lo traiga, y solo sale
   si se marca `en_lista = no`. Para saber en qué turnos estaba usa `turnos_previos.py` (memoria del último libro
   generado). `excepciones.py` queda para agregar o quitar a mano a alguien en ciertos días (por ejemplo, quien va
   en otra planilla).
4. `render_libro.py` llena un molde de Excel sin tocar zoom, márgenes ni alturas de fila (el renglón del libro
   físico), y fija los saltos de página.
5. `libro_firmas.py` orquesta y escribe `informe.txt`: diferencias contra el libro actual, docentes sin clases,
   excepciones vencidas, avisos de validación.

## Uso

```
python -m venv .venv
.venv\Scripts\python -m pip install pdfplumber openpyxl
.venv\Scripts\python libro_firmas.py "entrada\Profesores.pdf" --cursos "entrada\Cursos.pdf"
```

Necesita, en `datos/` (todo local, ignorado por git):

- `plantilla_libro.xlsx`: el libro de firmas convertido a `.xlsx`, con las hojas `prof. tm 2026` y `prof.tmyt.2026`
  (cinco bloques Lunes-Viernes de 4 columnas: N°, nombre, tratamiento, firma).
- `mdb_tratamiento.csv`: se genera con `exportar_mdb.ps1` (solo apellido, nombre y cargo).
- `docentes.csv` (se completa solo), `excepciones.csv` (a mano; ver `excepciones.py`) y `licencias.csv`
  (a mano: `docente;desde;hasta;motivo;en_lista`; ver `licencias.py`). `turnos_ultimo_libro.csv` lo escribe el programa.
- `horarios_manuales.csv` (opcional): horarios de docentes que vienen en un PDF escaneado o una foto y no se
  pueden leer por coordenadas. Se transcriben una vez y se revisan a ojo (formato en `horarios_manuales.py`).

Si falta el tratamiento (Profesor/Profesora) de un docente, **no se genera el libro**: no se adivina por el nombre.

## Tests

```
.venv\Scripts\python -m unittest discover -s tests -t .
```

## Privacidad

Este repositorio no contiene datos de personas. PDFs, planillas, listas de docentes y salidas están en
`.gitignore`; los tests usan nombres inventados. Antes de publicar cambios, revisar que no se haya colado un
nombre real.
