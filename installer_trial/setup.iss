; =====================================================================
;  PHASEINV2 - KSA E-Invoicing : TRIAL installer (embedded PostgreSQL)
;  Brand-new build - 2026-08-26
; =====================================================================
;  A single standalone Windows installer for the customer's device. It bundles
;  EVERYTHING the trial needs to run:
;    * the frozen application (Python runtime + every library + code/assets), and
;    * a PORTABLE PostgreSQL engine (bin/lib/share under _internal\pgsql).
;
;  The customer does NOT install PostgreSQL. On first launch the application
;  itself initialises a private database cluster under
;  %ProgramData%\PHASEINV2\pgdata, starts it on loopback (127.0.0.1:55432), and
;  provisions the schema automatically. There are therefore NO database
;  questions in this wizard - it just lays down the files.
;
;  Trial policy (enforced by the application, not the installer): 7 days OR
;  40 launches, whichever comes first.
; =====================================================================

#define MyAppName "PHASEINV2 E-Invoicing (Trial)"
#define MyAppShortName "PHASEINV2 Trial"
#define MyAppVersion "1.0.0-trial"
#define MyAppPublisher "PHASEINV2"
#define MyAppExeName "PHASEINV2.exe"

[Setup]
AppId={{7C2F9A14-3E51-4B8D-A6C7-9D0E1F2A3B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\PHASEINV2 Trial
DefaultGroupName={#MyAppShortName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=PHASEINV2_TRIAL_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableDirPage=no
UsePreviousAppDir=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\app\ui\assets\app_icon.ico
VersionInfoVersion=1.0.0
VersionInfoProductName={#MyAppShortName}
VersionInfoCompany={#MyAppPublisher}
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; The frozen application (onedir) - Python runtime + every library + portable
; PostgreSQL (under _internal\pgsql) + code/assets.
Source: "dist\PHASEINV2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Machine-wide writable data, ISOLATED under PHASEINV2_Trial so the trial never
; touches a production PHASEINV2 install. The embedded database cluster (pgdata),
; the trial license file, logs and backups all live here and MUST be
; user-writable so the app runs (and the DB server starts) without admin rights.
Name: "{commonappdata}\PHASEINV2_Trial"; Permissions: users-modify
Name: "{commonappdata}\PHASEINV2_Trial\logs"; Permissions: users-modify
Name: "{commonappdata}\PHASEINV2_Trial\Backups"; Permissions: users-modify
Name: "{commonappdata}\PHASEINV2_Trial\pgdata"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppShortName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppShortName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; A trial uninstall removes the embedded cluster and trial state so the machine
; is left clean. (Backups are intentionally NOT auto-deleted.)
Type: filesandordirs; Name: "{commonappdata}\PHASEINV2_Trial\pgdata"
Type: files; Name: "{commonappdata}\PHASEINV2_Trial\.license.dat"
Type: files; Name: "{commonappdata}\PHASEINV2_Trial\connection.json"

[Code]
{ Stop a running embedded server before uninstalling so its files are not locked. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  PgCtl, DataDir: String;
  Code: Integer;
begin
  if CurUninstallStep = usUninstall then begin
    PgCtl := ExpandConstant('{app}\_internal\pgsql\bin\pg_ctl.exe');
    DataDir := ExpandConstant('{commonappdata}\PHASEINV2_Trial\pgdata');
    if FileExists(PgCtl) and DirExists(DataDir) then
      Exec(PgCtl, '-D "' + DataDir + '" -m fast -w -t 20 stop',
           '', SW_HIDE, ewWaitUntilTerminated, Code);
  end;
end;
