# Cambios

Cada cambio sube la versión (`version.py`); la versión se ve abajo a la izquierda en la ventana.

## 1.6.3 — 2026-10-29
- Datos compartidos sin pisarse: Licencias, Horarios a mano y Excluidos se vuelven a leer cada vez que se abre la pantalla, y antes
  de agregar, editar o quitar se comprueba que otra PC no haya cambiado la lista (si cambió, se actualiza y avisa). Ya no hace
  falta cerrar y abrir el programa para ver lo que cargó la otra persona.

## 1.6.2 — 2026-10-29
- Arreglo: el instalador 1.6.0/1.6.1 escribía la carpeta de datos con UNA barra al principio (`\Servidor\...` en vez de
  `\\Servidor\...`), así que ninguna PC encontraba la carpeta compartida. Ahora la ruta se corrige sola al abrir (y se repara el
  `config.txt`), y `publicar.ps1` se niega a armar un instalador con una ruta mal escrita.

## 1.6.1 — 2026-10-29
- Si la carpeta de datos compartida no abre desde una PC, el aviso dice el motivo exacto que da Windows y ofrece elegir la carpeta a
  mano (se guarda en `config.txt` y el programa se reabre).

## 1.6.0 — 2026-10-29
- Datos compartidos entre PC: `config.txt` (`Datos=carpeta de red`) hace que licencias, excluidos, docentes y horarios a mano se
  vean igual en todas las PC; si no hay red avisa y usa la copia local.
- Instalador (Inno Setup) y ícono propio; el zip pasa a ser la versión portable.

## 1.5.0 — 2026-10-29
- Versión numerada y visible; este registro de cambios.
- Se puede instalar en otra PC (`publicar.ps1` arma una carpeta lista para copiar, sin necesidad de Python).
- `tm`: el área de impresión corta en la columna V (no sale una página en blanco).

## 1.4.0 — 2026-10-29
- Excel: bordes iguales en todos los días (martes y jueves quedaban abiertos), rótulos de día parejos.
- Barra de progreso continua junto al contador de segundos.

## 1.3.0 — 2026-10-29
- Informe completo en tarjetas legibles, con "Qué hacer" en cada sección.

## 1.2.0 — 2026-10-28
- Pantalla Excluidos; nombres con inicial o nombre compuesto se reconocen como la misma persona.
- Contador de segundos al armar.

## 1.1.0 — 2026-10-28
- Ventana con el formato de Movimientos Docentes y Registro de Egresados (barra lateral índigo, tarjetas).

## 1.0.0 — 2026-10-28
- Primera versión de la app de escritorio: armar libro, Licencias, Horarios a mano.
