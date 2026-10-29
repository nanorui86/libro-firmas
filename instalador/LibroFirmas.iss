; Instalador de Libro de firmas docente (Inno Setup 6). Se genera con:  .\publicar.ps1
; No pide permisos de administrador. Copia el programa y crea los accesos directos. Los datos (docentes, licencias,
; excluidos, plantilla...) viven en una carpeta compartida de la red: se copian ahi solo si todavia no existen, y
; config.txt (que se crea solo si falta) apunta a esa carpeta. Para actualizar: ejecutar el instalador nuevo encima.

#define AppVersion GetEnv("LIBRO_VERSION")
#if AppVersion == ""
  #define AppVersion "1.0.0"
#endif
; La carpeta compartida de datos la pasa publicar.ps1 (variable LIBRO_DATOS, leida de datos/ruta_red.txt, que no se versiona).
#define CarpetaDatos GetEnv("LIBRO_DATOS")
#if CarpetaDatos == ""
  #error Falta LIBRO_DATOS: usar publicar.ps1
#endif

[Setup]
AppId={{B2E4C6A8-5D31-4F7A-9C20-7A1E3D5F8B64}
AppName=Libro de firmas docente
AppVersion={#AppVersion}
AppPublisher=Colegio Hölters
DefaultDirName=C:\LibroFirmas
DefaultGroupName=Libro de firmas docente
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
OutputDir=Salida
OutputBaseFilename=LibroFirmas-Setup-{#AppVersion}
SetupIconFile=..\recursos\app.ico
UninstallDisplayIcon={app}\Libro de firmas.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Dirs]
Name: "{app}\entrada"
Name: "{app}\salida"

[Files]
Source: "..\publicacion\paquete\Libro de firmas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "datos\*,entrada\*,salida\*,config.txt,app_config.json,error_app.txt"
; Datos compartidos: se embeben y se copian por codigo (ver [Code]) solo si todavia no existen; si la red falla, no se aborta.
Source: "..\datos\plantilla_libro.xlsx"; DestDir: "{tmp}"; Flags: dontcopy
Source: "..\datos\docentes.csv"; DestDir: "{tmp}"; Flags: dontcopy
Source: "..\datos\mdb_tratamiento.csv"; DestDir: "{tmp}"; Flags: dontcopy skipifsourcedoesntexist
Source: "..\datos\excepciones.csv"; DestDir: "{tmp}"; Flags: dontcopy skipifsourcedoesntexist
Source: "..\datos\licencias.csv"; DestDir: "{tmp}"; Flags: dontcopy skipifsourcedoesntexist
Source: "..\datos\horarios_manuales.csv"; DestDir: "{tmp}"; Flags: dontcopy skipifsourcedoesntexist
Source: "..\datos\turnos_ultimo_libro.csv"; DestDir: "{tmp}"; Flags: dontcopy skipifsourcedoesntexist

[Icons]
Name: "{group}\Libro de firmas"; Filename: "{app}\Libro de firmas.exe"
Name: "{autodesktop}\Libro de firmas"; Filename: "{app}\Libro de firmas.exe"; Tasks: escritorio

[Run]
Filename: "{app}\Libro de firmas.exe"; Description: "Abrir Libro de firmas"; Flags: nowait postinstall skipifsilent

[Code]
// Los datos viven en una carpeta compartida de la red. Si no se puede abrir (sin red), el programa se instala igual y se avisa.
var
  SinDatos: Boolean;

function InitializeSetup: Boolean;
begin
  Result := True;
  SinDatos := not (DirExists('{#CarpetaDatos}') or ForceDirectories('{#CarpetaDatos}'));
  if SinDatos then
    MsgBox('No se pudo abrir la carpeta de datos compartida:' + #13#10 + '{#CarpetaDatos}' + #13#10#13#10 +
           'El programa se instala igual, pero no va a encontrar los datos hasta que haya conexión a la red.', mbInformation, MB_OK);
end;

// Copia cada archivo de datos solo si todavia no existe en la carpeta compartida (nunca pisa lo que ya cargaron las demas PC).
procedure CopiarDatosIniciales;
var
  Nombres: array of String;
  I: Integer;
  Destino: String;
begin
  SetArrayLength(Nombres, 7);
  Nombres[0] := 'plantilla_libro.xlsx';
  Nombres[1] := 'docentes.csv';
  Nombres[2] := 'mdb_tratamiento.csv';
  Nombres[3] := 'excepciones.csv';
  Nombres[4] := 'licencias.csv';
  Nombres[5] := 'horarios_manuales.csv';
  Nombres[6] := 'turnos_ultimo_libro.csv';
  for I := 0 to GetArrayLength(Nombres) - 1 do
  begin
    Destino := '{#CarpetaDatos}\' + Nombres[I];
    if not FileExists(Destino) then
    begin
      try
        ExtractTemporaryFile(Nombres[I]);
        FileCopy(ExpandConstant('{tmp}\') + Nombres[I], Destino, True);
      except
        // archivo que no viajaba en el instalador: se sigue con el siguiente
      end;
    end;
  end;
end;

// config.txt: se crea solo si no existe (asi una actualizacion no pisa lo configurado). UTF-8 por las tildes.
procedure CurStepChanged(CurStep: TSetupStep);
var
  Cfg: String;
  Lineas: TArrayOfString;
begin
  if CurStep = ssPostInstall then
  begin
    if not SinDatos then
      CopiarDatosIniciales;
    Cfg := ExpandConstant('{app}\config.txt');
    if not FileExists(Cfg) then
    begin
      SetArrayLength(Lineas, 2);
      Lineas[0] := '# Configuración de Libro de firmas. Datos = carpeta compartida con los registros.';
      Lineas[1] := 'Datos={#CarpetaDatos}';
      SaveStringsToUTF8File(Cfg, Lineas, False);
    end;
  end;
end;
