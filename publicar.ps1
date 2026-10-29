# Arma la carpeta "Libro de firmas" lista para copiar a otra PC (no necesita Python ni instalar nada).
# Uso:  powershell -ExecutionPolicy Bypass -File publicar.ps1
# Salida: publicacion\Libro de firmas <version>.zip  (y la carpeta sin comprimir en publicacion\paquete)
# OJO: el paquete lleva la carpeta datos\ (nombres de docentes): no subirlo a GitHub ni a lugares publicos.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$version = (Select-String -Path "version.py" -Pattern 'VERSION\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
Write-Host "Version $version"

$pub = Join-Path $PSScriptRoot "publicacion"
if (Test-Path $pub) { Remove-Item $pub -Recurse -Force }
New-Item -ItemType Directory -Path $pub | Out-Null

& $py -m PyInstaller --noconfirm --clean --windowed --onedir --name "Libro de firmas" `
    --distpath "$pub\paquete" --workpath "$pub\work" --specpath "$pub" `
    --paths "$PSScriptRoot" `
    --collect-all pdfplumber --collect-all pdfminer --collect-all pypdfium2 `
    lanzador.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo" }

$carpeta = "$pub\paquete\Libro de firmas"
New-Item -ItemType Directory -Path "$carpeta\datos", "$carpeta\entrada", "$carpeta\salida" | Out-Null
foreach ($f in "plantilla_libro.xlsx", "docentes.csv", "mdb_tratamiento.csv", "excepciones.csv", "licencias.csv", "horarios_manuales.csv", "turnos_ultimo_libro.csv") {
    $origen = Join-Path $PSScriptRoot "datos\$f"
    if (Test-Path $origen) { Copy-Item $origen "$carpeta\datos\$f" } else { Write-Warning "Falta datos\$f" }
}
Copy-Item "CHANGELOG.md" "$carpeta\CHANGELOG.md"
@"
LIBRO DE FIRMAS DOCENTE - version $version

Para usarlo en otra PC:
1. Copie esta carpeta completa (Libro de firmas) a la PC, por ejemplo a C:\Libro de firmas.
2. Haga doble clic en "Libro de firmas.exe". (Si Windows avisa que es de un editor desconocido: Mas informacion > Ejecutar de todas formas.)
3. Opcional: clic derecho en el .exe > Enviar a > Escritorio (crear acceso directo).

Que hay en la carpeta:
- datos\   : la plantilla del libro y los registros (docentes, licencias, excluidos, horarios a mano). Se editan desde el programa.
- entrada\ : aca se guardan los PDF de Untis que se bajan.
- salida\  : aca queda el libro armado (Excel) y el informe.

Importante: cada PC tiene su propia copia de datos\. Si carga una licencia o excluye a alguien en una PC, no se ve en la otra.
Para llevar los cambios de una PC a otra, copie la carpeta datos\ completa.
Necesita Microsoft Excel para abrir e imprimir el libro.
"@ | Set-Content -Path "$carpeta\LEEME.txt" -Encoding ASCII

$zip = "$pub\Libro de firmas $version.zip"
Compress-Archive -Path $carpeta -DestinationPath $zip
Write-Host ("Listo: {0} ({1:N0} MB)" -f $zip, ((Get-Item $zip).Length / 1MB))
