# Exporta SOLO Tratamiento, Nombre, Apellidos y Cargo del .mdb de docentes a datos\mdb_tratamiento.csv.
# El .mdb tiene además DNI, teléfonos y mails: no se leen ni se copian.
# Nota: en ese .mdb la columna "Tratamiento" trae "APELLIDO, NOMBRE" y el género está en "CARGO"
# (PROFESOR / PROFESORA); por eso maestro.py usa Apellidos, Nombre y Cargo.
param([Parameter(Mandatory)][string]$Mdb)
$tmp = Join-Path $env:TEMP "docentes_tmp.mdb"
Copy-Item -LiteralPath $Mdb $tmp -Force          # se lee una copia, nunca el original
$cn = New-Object -ComObject ADODB.Connection
$cn.Open("Provider=Microsoft.ACE.OLEDB.12.0;Data Source=$tmp;Mode=Read")
$rs = $cn.Execute("SELECT Tratamiento, Nombre, Apellidos, CARGO FROM [LISTA PROF ACTUALIZAR]")
$filas = while (-not $rs.EOF) {
    [pscustomobject]@{ Tratamiento = [string]$rs.Fields.Item(0).Value; Nombre = [string]$rs.Fields.Item(1).Value
                       Apellidos = [string]$rs.Fields.Item(2).Value; Cargo = [string]$rs.Fields.Item(3).Value }
    $rs.MoveNext()
}
$cn.Close(); Remove-Item $tmp -Force
New-Item -ItemType Directory -Force (Join-Path $PSScriptRoot "datos") | Out-Null
$filas | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $PSScriptRoot "datos\mdb_tratamiento.csv")
"$(@($filas).Count) filas exportadas"
