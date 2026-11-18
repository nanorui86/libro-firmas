# Lista de preceptores en la app: diseño

Fecha: 2026-11-18. Versión objetivo: 1.7.0.

## Para qué
La hoja `prec. 2026` del libro de firmas (la lista de preceptores, ayudantes y jefa de preceptores que firman cada día) hoy se arma
a mano en Excel. El usuario quiere armarla e imprimirla desde la misma app que el libro de docentes, para tener todo en un lugar,
con el mismo formato impreso de siempre.

## Cómo es la hoja hoy (molde `prec. 2026`, ya incluido en `datos/plantilla_libro.xlsx`)
- Una sola hoja (no hay división tm/tmyt). Cinco bloques de día: Lunes, Martes, Viernes y Miércoles en fila arriba y Jueves debajo
  (arranca en la fila 31). Cada bloque: N° | `APELLIDO, Nombre` | cargo | columna de firma en blanco, con 23 renglones.
- Orden alfabético por apellido. Cargos que aparecen: Preceptor/a, P.A. (o PA), Jefa de Precep., Ay. de Lab.
- La lista casi nunca cambia. Cuatro días tienen las mismas personas y otro día tiene menos (faltan tres). Mañana/tarde no se imprime.
- Un apellido con apóstrofo hoy se escribe con `^` por una limitación del tipeo; en la app va con apóstrofo (`'`).

## Objetivos
- Pantalla **Preceptores** en la app, con el mismo estilo que Licencias, Excluidos y Horarios a mano (tabla con Agregar, Editar, Quitar).
- Una fila por persona: Apellido, Nombre, Cargo y cinco casillas L M X J V, todas tildadas por defecto. Flexibilidad: tildar o destildar
  un día, agregar o quitar personas.
- Salir en el mismo Excel que el libro de docentes (hoja `prec. 2026`, mismo formato, mismo orden, mismas medidas), y también poder
  armar solo esa hoja sin necesidad de los PDF de Untis.
- Datos compartidos entre PC, como el resto (`preceptores.csv` en la carpeta de datos).
- **Licencias de preceptores**, con el mismo criterio que las de docentes (ver Decisiones).
- **La hoja crece sola** si hay más de 23 personas en un día, sin que el usuario tenga que pedirlo cuando necesite imprimir.

## No objetivos
- No hay turno mañana/tarde para preceptores (todos van juntos en una lista) ni se lee Untis para ellos.
- No se imprime solo: la app abre Excel y explica cómo imprimir, como con el libro de docentes.
- No se escribe nunca sobre el Excel original de la red.

## Qué sería un fracaso aunque "ande"
- Que la hoja impresa no coincida con la actual (renglones, anchos, saltos de página, bordes): se pega en el libro físico.
- Que un nombre real quede en el repo público o que la hoja se pise entre dos PC.

## Restricciones
- Repo público: `datos/` está ignorado; los tests usan nombres inventados; nada de nombres reales ni de la ruta de red en `docs/` ni en el código.
- Cada cambio sube la versión y se ve en la ventana (1.7.0 + CHANGELOG).
- Cada bloque tiene 23 renglones y hoy hay 22 personas. Con más de 23 en un día la hoja se amplía (ver Decisiones); nunca se corta una lista.
- Los preceptores NO deben entrar en `licencias.csv` (el de docentes): ahí el armado del libro de docentes los trataría como docentes
  de licencia y se detendría ("no se sabe en qué días y turnos figuraba"). Sus licencias viven en su propio archivo.
- No se toca el zoom (100) ni las alturas de fila (34/35 pt), como en las otras hojas.

## Enfoques considerados
1. **Una fila por persona con casillas por día (elegido).** Se ve todo de un vistazo y un cambio puntual es un clic.
2. Solo excepciones ("no viene tal día"): menos filas, pero no se ve quién viene cada día.
3. Una fila por persona y día: ocho de cada diez filas serían iguales y hay que cargarlas cinco veces.

## Decisiones
Las del usuario:
- Opción 1. El orden y el formato impreso son los de hoy (alfabético). Apellido con apóstrofo.

Mías (para corregir si no cuadran):
- **Datos:** `datos/preceptores.csv` con `apellido;nombre;cargo;dias;lic_desde;lic_hasta;lic_motivo;en_lista` (días como
  `lunes,martes,...`; las cuatro últimas columnas van vacías si no hay licencia), junto a las licencias de docentes en la carpeta
  compartida.
- **Licencias:** misma lógica que en docentes. El formulario de la persona tiene una parte opcional de licencia: Desde, Hasta (puede
  quedar vacío), Motivo y ¿Sigue en la lista? (Sí por defecto). Mientras la licencia está vigente (la fecha de hoy entre desde y hasta),
  con "Sí" la persona sigue en sus días de siempre y con "No" sale de la lista; al vencer, vuelve sola. La tabla muestra una columna
  "Estado hoy" (Vigente, Vencida, Todavía no empezó) con el mismo código que Licencias (`repositorio.estado_licencia`, `MOTIVOS`, fechas
  día/mes/año). El informe lista las licencias vigentes de preceptores y avisa de una sin fecha de fin o ya vencida, sin cambiar el libro.
- **Hoja que crece:** los bloques son de 23 renglones. Con más de 23 personas en algún día, todos los bloques ganan renglones de a una
  página (24, como en el libro de docentes) y el bloque de Jueves baja lo necesario, de modo que ninguno se superponga. Con 23 o menos,
  la hoja sale idéntica a la actual. El que construye define dónde cae el corte de página y lo comprueba exportando a PDF. Se carga una sola vez desde la hoja actual (todos los días de cada persona) y llega a la carpeta compartida con el
  instalador, como los otros archivos de datos (solo si falta).
- **Impreso:** `APELLIDO, Nombre`; el apellido se pasa a mayúsculas solo, el nombre queda como se escribió. El cargo se imprime tal cual
  se cargó (la carga inicial respeta lo que hoy dice la hoja, aunque haya `P.A.` y `PA`); el campo ofrece los cargos existentes pero admite otro.
- **Orden:** el mismo criterio que los docentes (alfabético sin tildes).
- **Salida:** el armado normal agrega la hoja `prec. 2026` al mismo Excel. La pantalla Preceptores tiene además "Armar lista de
  preceptores", que genera un Excel con solo esa hoja y lo abre, sin necesitar los PDF. Así un error de Untis no bloquea la lista de preceptores.
- **Misma protección que las otras tablas:** relectura al abrir la pantalla y comprobación de cambios de otra PC antes de guardar.
- **Informe:** cuántas personas hay por día y las licencias (arriba); sin avisos de Untis.

## Qué queda al que construye
- Extender `Formulario` para un grupo de casillas (L M X J V) y mostrar en la tabla algo como `✔ ✔ ✔ ✔ ·`.
- `repositorio.py`: leer/validar/guardar preceptores (apellido y nombre obligatorios, al menos un día, sin repetidos, licencia válida
  con el mismo `validar_licencia`) y calcular quién figura cada día para una fecha dada.
- `render_libro.py`: función para escribir los 5 bloques sobre el molde `prec. 2026` (los bloques empiezan en las columnas A, E, I, M y
  el de Jueves en I31; las filas alternan 34 pt de renglón con 5 pt de separación; verificar rótulos y bordes contra el molde),
  manteniendo esa hoja cuando se arma el libro completo, y con la ampliación descrita.
- Comprobar la paginación exportando a PDF con Excel y compararla con la hoja original (misma cantidad de páginas y mismos cortes) con
  22 personas, y probar también con 24 y con 50 para ver la ampliación.
- Tests con nombres inventados, `CHANGELOG`, `ESTADO.md`, versión 1.7.0 y el archivo en el instalador.
- La prueba física de impresión queda para el usuario, como con el libro de docentes.
