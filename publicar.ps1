# Arma el programa para otras PC: un .zip portable y el instalador (Inno Setup 6).
# Uso:  powershell -ExecutionPolicy Bypass -File publicar.ps1
# Salida: publicacion\Libro de firmas <version>.zip  y  instalador\Salida\LibroFirmas-Setup-<version>.exe
# La carpeta compartida de datos sale de datos\ruta_red.txt (no se versiona) o de la variable LIBRO_DATOS.
# OJO: el zip y el instalador llevan nombres de docentes: no subirlos a GitHub ni a lugares publicos.
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
    --paths "$PSScriptRoot" --icon "$PSScriptRoot\recursos\app.ico" --add-data "$PSScriptRoot\recursos;recursos" `
    --collect-all pdfplumber --collect-all pdfminer --collect-all pypdfium2 `
    lanzador.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo" }

# Zip portable (lleva su propia copia de datos\; el instalador, en cambio, usa la carpeta compartida).
$carpeta = "$pub\paquete\Libro de firmas"
$portable = "$pub\portable\Libro de firmas"
New-Item -ItemType Directory -Path "$pub\portable" | Out-Null
Copy-Item $carpeta $portable -Recurse
New-Item -ItemType Directory -Path "$portable\datos", "$portable\entrada", "$portable\salida" | Out-Null
foreach ($f in "plantilla_libro.xlsx", "docentes.csv", "mdb_tratamiento.csv", "excepciones.csv", "licencias.csv", "horarios_manuales.csv", "turnos_ultimo_libro.csv") {
    $origen = Join-Path $PSScriptRoot "datos\$f"
    if (Test-Path $origen) { Copy-Item $origen "$portable\datos\$f" } else { Write-Warning "Falta datos\$f" }
}
Copy-Item "CHANGELOG.md" "$portable\CHANGELOG.md"
@"
LIBRO DE FIRMAS DOCENTE - version $version  (version portable)

1. Copie esta carpeta completa a la PC, por ejemplo a C:\Libro de firmas.
2. Doble clic en "Libro de firmas.exe". (Si Windows avisa que es de un editor desconocido: Mas informacion > Ejecutar de todas formas.)

Esta version guarda los datos en su propia carpeta datos\ (no se comparten con otras PC).
Para compartir los datos entre PC, use el instalador, o cree un archivo config.txt junto al .exe con una linea:
    Datos=\servidor\carpeta
y copie alli el contenido de datos\.
Necesita Microsoft Excel para abrir e imprimir el libro.
"@ | Set-Content -Path "$portable\LEEME.txt" -Encoding ASCII
$zip = "$pub\Libro de firmas $version.zip"
Compress-Archive -Path $portable -DestinationPath $zip
Write-Host ("Zip: {0} ({1:N0} MB)" -f $zip, ((Get-Item $zip).Length / 1MB))

# Instalador
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Falta Inno Setup 6 (winget install JRSoftware.InnoSetup --scope user)." }
if (-not $env:LIBRO_DATOS) {
    $rutaRed = Join-Path $PSScriptRoot "datos\ruta_red.txt"
    if (-not (Test-Path $rutaRed)) { throw "Falta datos\ruta_red.txt (o la variable LIBRO_DATOS) con la carpeta compartida de datos." }
    $env:LIBRO_DATOS = (Get-Content $rutaRed -Raw -Encoding UTF8).Trim()
}
$env:LIBRO_VERSION = $version
& $iscc /Q (Join-Path $PSScriptRoot "instalador\LibroFirmas.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo" }
$exe = Get-Item "instalador\Salida\LibroFirmas-Setup-$version.exe"
Write-Host ("Instalador: {0} ({1:N0} MB)" -f $exe.FullName, ($exe.Length / 1MB))
