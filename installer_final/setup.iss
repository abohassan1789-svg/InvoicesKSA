; =====================================================================
;  PHASEINV2 - KSA E-Invoicing : FINAL unified installer
;  Brand-new build - 2026-08-22 (v4.6.0)
; =====================================================================
;  A single standalone Windows installer for the customer's device. It bundles
;  the WHOLE frozen application - the Python runtime, EVERY library and all code
;  and assets - so nothing else has to be installed for the application itself to
;  run. It handles BOTH deployment scenarios from one file:
;
;    * Local Mode           - PostgreSQL is on THIS computer (localhost).
;    * Internal Server Mode - PostgreSQL is on another computer / server on the
;                             internal network (localhost is rejected).
;
;  PostgreSQL is NOT bundled: it is installed manually before running this setup.
;  Both modes verify the server is actually reachable and say so plainly if it is
;  not, rather than installing a database engine.
;
;  At install time the wizard: tests the connection, creates the application
;  database only if it is missing (never dropped/overwritten), writes the
;  encrypted connection profile to %ProgramData%\PHASEINV2\connection.json, and
;  provisions the schema + default admin/roles/permissions idempotently via the
;  bundled phaseinv2-config.exe (the same code path the application uses). The
;  database password is never written to any log or placed on a command line.
; =====================================================================

#define MyAppName "PHASEINV2 E-Invoicing"
#define MyAppShortName "PHASEINV2 E-Invoicing"
; v4.8.0 (2026-09-12): invoice-level percentage discount before VAT (new additive
;   schema columns invoice_discount_rate/amount + subtotal_after_discount, applied
;   idempotently to the returning client's existing DB — verified non-destructive)
;   + Saudi invoice print updates (النموذج التاسع/العاشر discount breakdown, text
;   wrap for long seller/customer values, and العاشر items-table column changes).
; v4.9.0 (2026-09-13): two-way invoice discount entry — typing the discount AMOUNT
;   is now accepted and kept exactly (percentage derived from it), mirroring the
;   existing rate→amount direction. No schema change (same columns as v4.8.0).
; v4.10.0 (2026-09-16): UI/print-only, no schema change (same columns as v4.8.0):
;   - المرحلة الثانية preview picker: hid 4 templates (الخطوط السعودية/المتكاملة/
;     الإسناد الماسي/اقاسيم); added النموذج الثاني عشر (= م1 الخامس عشر) والثالث عشر
;     (= م1 السابع عشر) as Phase-2 signed-QR copies.
;   - Sales-invoice entry: hid the discount rows (نسبة الخصم/قيمة الخصم/الإجمالي بعد
;     الخصم) from the totals panel. Fields stay at 0.00 so totals stay correct.
; v4.11.0 (2026-09-16): UI/print-only, no schema change (same columns as v4.8.0):
;   - New fixed-brand ZATCA replica template «مواسم الفاكهة» (saudi_invoice_print_v13,
;     logo asset mawsim_fruitseason_logo.png) on BOTH pickers — Phase-2 choice 14 &
;     Phase-1 option 16. Fixed seller identity + logo; customer/items/totals/QR live.
;   - Its meta strip shows only Invoice/Due/Supply Date (Source & Salesman hidden).
; v4.14.0 (2026-10-07): ADDITIVE schema only, safe for a returning client's DB:
;   - sales_invoice_lines.item_description (وصف الصنف, nullable) + «إظهار وصف الصنف».
;   - companies.commercial_registration optional (DROP NOT NULL + not-blank CHECK).
;   - New invoice templates v14..v21, vouchers v10..v12, print-option tweaks.
; v4.15.0 (2026-10-21): ADDITIVE schema only (two NEW tables, no existing table
;   touched), safe for a returning client's DB. First build from InvoicesKSA_publish:
;   - «مصادقة على الرصيد» screen (balance_confirmations, migration 021) + 4 layouts.
;   - «عقود التوريد» screen (supply_contracts + show_stamp, migrations 022/023) + 5 layouts.
;   - Invoice templates v22..v28 («نهلة الخليج» = choice 21, «البركة» = choice 22),
;     customer statements 4..23 (stamp on all), receipt vouchers 16..23,
;     embedded Noto Naskh Arabic fonts.
#define MyAppVersion "4.15.0"
#define MyAppPublisher "PHASEINV2"
#define MyAppExeName "PHASEINV2.exe"
#define ConfigExeName "phaseinv2-config.exe"

[Setup]
; AppId is the in-place-upgrade identity. Kept stable so this build upgrades any
; previous PHASEINV2 install on the customer's machine instead of installing a
; second copy side by side.
AppId={{B8D31F42-6A7C-4E59-9F30-1C2E4A6B8D01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf}\PHASEINV2
DefaultGroupName={#MyAppShortName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=PHASEINV2_Setup
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
; Stamp the version into the setup EXE's own file properties so support can ask a
; customer to right-click the installer instead of guessing which build they have.
VersionInfoVersion={#MyAppVersion}
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
; The frozen application (onedir) - Python runtime + every library + code/assets.
Source: "dist\PHASEINV2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The installer-only configuration helper (connection test, create-db, provision,
; write profile). Shipped as a temporary file so it is not left in Program Files.
Source: "dist\{#ConfigExeName}"; Flags: dontcopy
; NOTE: PostgreSQL is deliberately NOT bundled - installed manually beforehand.

[Dirs]
; Machine-wide writable data (profile, logs, backups). Granted modify to standard
; users so the application runs without administrator privileges.
Name: "{commonappdata}\PHASEINV2"; Permissions: users-modify
Name: "{commonappdata}\PHASEINV2\logs"; Permissions: users-modify
Name: "{commonappdata}\PHASEINV2\Backups"; Permissions: users-modify
; The chosen backup folder - same modify grant, or it silently produces zero backups.
Name: "{code:GetBackupDir}"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppShortName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppShortName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
var
  ModePage: TInputOptionWizardPage;
  LocalPage: TInputQueryWizardPage;
  ServerPage: TInputQueryWizardPage;
  BackupPage: TInputDirWizardPage;
  InstallMode: Integer;          { 0 = Local, 1 = Internal Server }
  DbHost: String;
  DbPort: Integer;
  DbName: String;
  DbUser: String;
  DbPass: String;
  DbSslMode: String;
  ConfigExe: String;
  ProfilePath: String;
  LogFile: String;

const
  MODE_LOCAL = 0;
  MODE_SERVER = 1;

function IsLocalMode: Boolean;
begin
  Result := InstallMode = MODE_LOCAL;
end;

function ModeName: String;
begin
  if IsLocalMode then Result := 'Local' else Result := 'InternalServer';
end;

procedure AppendInstallLog(Msg: String);
var
  Existing: AnsiString;
begin
  if LogFile = '' then
    exit;
  Existing := '';
  LoadStringFromFile(LogFile, Existing);
  SaveStringToFile(
    LogFile,
    Existing + AnsiString('[' + GetDateTimeString('yyyy/mm/dd hh:nn:ss', '-', ':') + '] ' + Msg + #13#10),
    False);
end;

function IsLoopbackAddress(Address: String): Boolean;
var
  A: String;
begin
  A := Lowercase(Trim(Address));
  Result := (A = 'localhost') or (A = '127.0.0.1') or (A = '::1') or (Copy(A, 1, 4) = '127.');
end;

procedure InitializeWizard;
begin
  InstallMode := MODE_LOCAL;
  DbHost := '127.0.0.1';
  DbPort := 5432;
  DbSslMode := 'prefer';
  ProfilePath := ExpandConstant('{commonappdata}\PHASEINV2\connection.json');

  { The configuration helper is bundled as a temporary file and only needed by
    the installer; extract it up front so page-level connection tests can run. }
  ExtractTemporaryFile('{#ConfigExeName}');
  ConfigExe := ExpandConstant('{tmp}\{#ConfigExeName}');

  ModePage := CreateInputOptionPage(
    wpSelectDir,
    'Database Mode',
    'Choose how this device connects to PostgreSQL.',
    'Local Mode uses PostgreSQL on THIS computer. Internal Server Mode connects to a PostgreSQL database on another computer or server on your internal network.',
    True,
    False);
  ModePage.Add('Local Mode  -  PostgreSQL on this computer (localhost)');
  ModePage.Add('Internal Server Mode  -  PostgreSQL on another computer / server');
  ModePage.SelectedValueIndex := 0;

  LocalPage := CreateInputQueryPage(
    ModePage.ID,
    'Local Database Settings',
    'PostgreSQL on this computer (localhost / 127.0.0.1).',
    'PostgreSQL must already be installed on this computer - this setup does not install it. Enter the database name, port and the PostgreSQL superuser credentials.');
  LocalPage.Add('Database name:', False);
  LocalPage.Add('PostgreSQL port:', False);
  LocalPage.Add('PostgreSQL username:', False);
  LocalPage.Add('PostgreSQL password:', True);
  LocalPage.Values[0] := 'InvPhase2';
  LocalPage.Values[1] := '5432';
  LocalPage.Values[2] := 'postgres';
  LocalPage.Values[3] := '';

  ServerPage := CreateInputQueryPage(
    LocalPage.ID,
    'Internal Server Settings',
    'PostgreSQL on another computer / server.',
    'Enter the server address and PostgreSQL credentials. The address must be a hostname or IP on your network - it cannot be localhost or 127.0.0.1.');
  ServerPage.Add('Server host or IP:', False);
  ServerPage.Add('Port:', False);
  ServerPage.Add('Database name:', False);
  ServerPage.Add('Username:', False);
  ServerPage.Add('Password:', True);
  ServerPage.Add('SSL mode (disable / prefer / require):', False);
  ServerPage.Values[0] := '';
  ServerPage.Values[1] := '5432';
  ServerPage.Values[2] := 'InvPhase2';
  ServerPage.Values[3] := 'postgres';
  ServerPage.Values[4] := '';
  ServerPage.Values[5] := 'prefer';

  { Where the application writes its automatic backups. It takes one on open
    (only if none was taken today) and one on close, via pg_dump. }
  BackupPage := CreateInputDirPage(
    ServerPage.ID,
    'Backup Folder',
    'Where should the automatic database backups be stored?',
    'The application automatically backs up the database when it opens (once a day) and when it closes. Choose the folder for those backup files. You can select an external drive or a network folder; if it is unavailable at run time the application falls back to the default folder rather than failing to open.',
    False, '');
  BackupPage.Add('Backup folder:');
  BackupPage.Values[0] := ExpandConstant('{commonappdata}\PHASEINV2\Backups');
end;

{ Exposed to [Dirs] so the chosen folder is created with users-modify. Called
  before the wizard exists during silent/uninstall passes, hence the guard. }
function GetBackupDir(Param: String): String;
begin
  if BackupPage = nil then
    Result := ExpandConstant('{commonappdata}\PHASEINV2\Backups')
  else
    Result := Trim(BackupPage.Values[0]);
  if Result = '' then
    Result := ExpandConstant('{commonappdata}\PHASEINV2\Backups');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (PageID = LocalPage.ID) and (not IsLocalMode) then
    Result := True;
  if (PageID = ServerPage.ID) and IsLocalMode then
    Result := True;
end;

{ Run the configuration helper, capture its output to the install log (never the
  password - the CLI scrubs it and the password only ever travels via a file),
  and return the process exit code (0 = success). }
function RunConfigLogged(StepName, Args: String): Integer;
var
  OutFile, FullCmd: String;
  Content: AnsiString;
  Code: Integer;
begin
  OutFile := ExpandConstant('{tmp}\cfg-out.txt');
  DeleteFile(OutFile);
  FullCmd := '/C ""' + ConfigExe + '" ' + Args + ' > "' + OutFile + '" 2>&1"';
  if not Exec(ExpandConstant('{cmd}'), FullCmd, ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, Code) then
    Code := -1;
  Content := '';
  LoadStringFromFile(OutFile, Content);
  AppendInstallLog('[' + StepName + '] exit=' + IntToStr(Code) + '  ' + String(Content));
  Result := Code;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  PortNum, Code: Integer;
  PwFile: String;
begin
  Result := True;

  if CurPageID = ModePage.ID then begin
    InstallMode := ModePage.SelectedValueIndex;
    exit;
  end;

  if CurPageID = LocalPage.ID then begin
    DbName := Trim(LocalPage.Values[0]);
    PortNum := StrToIntDef(Trim(LocalPage.Values[1]), -1);
    DbUser := Trim(LocalPage.Values[2]);
    DbPass := LocalPage.Values[3];
    DbHost := '127.0.0.1';
    DbSslMode := 'prefer';
    if DbName = '' then begin
      MsgBox('Database name is required.', mbError, MB_OK); Result := False; exit;
    end;
    if (PortNum < 1) or (PortNum > 65535) then begin
      MsgBox('Port must be between 1 and 65535.', mbError, MB_OK); Result := False; exit;
    end;
    if DbUser = '' then begin
      MsgBox('PostgreSQL username is required.', mbError, MB_OK); Result := False; exit;
    end;
    if DbPass = '' then begin
      MsgBox('PostgreSQL password is required.', mbError, MB_OK); Result := False; exit;
    end;
    DbPort := PortNum;

    { Pre-flight test: setup does not install PostgreSQL, so if it is not there
      yet the customer must find out here, not after a "successful" install. }
    PwFile := ExpandConstant('{tmp}\pgpass.txt');
    if not SaveStringToFile(PwFile, DbPass, False) then begin
      MsgBox('Could not create a temporary file to test the connection.', mbError, MB_OK);
      Result := False; exit;
    end;
    WizardForm.StatusLabel.Caption := 'Testing the local PostgreSQL connection...';
    Code := RunConfigLogged('preflight-test-local',
      'test-db --host 127.0.0.1 --port ' + IntToStr(DbPort) +
      ' --db postgres --user "' + DbUser + '" --password-file "' + PwFile +
      '" --sslmode prefer');
    DeleteFile(PwFile);
    if Code <> 0 then begin
      if MsgBox('Could not connect to PostgreSQL on this computer at 127.0.0.1:' + IntToStr(DbPort) + '.' + #13#10 + #13#10 +
                'This setup does not install PostgreSQL - it must be installed on this computer first.' + #13#10 + #13#10 +
                'Please check that:' + #13#10 +
                '  - PostgreSQL is installed and its service is running,' + #13#10 +
                '  - the port is correct (default 5432),' + #13#10 +
                '  - the username and password are correct.' + #13#10 + #13#10 +
                'Continue anyway? The application will let you fix the connection on first launch.',
                mbError, MB_YESNO) <> IDYES then begin
        Result := False; exit;
      end;
      AppendInstallLog('Local pre-flight failed; user chose to continue anyway.');
    end;
    exit;
  end;

  if CurPageID = ServerPage.ID then begin
    DbHost := Trim(ServerPage.Values[0]);
    PortNum := StrToIntDef(Trim(ServerPage.Values[1]), -1);
    DbName := Trim(ServerPage.Values[2]);
    DbUser := Trim(ServerPage.Values[3]);
    DbPass := ServerPage.Values[4];
    DbSslMode := Lowercase(Trim(ServerPage.Values[5]));
    if DbHost = '' then begin
      MsgBox('Server host or IP is required.', mbError, MB_OK); Result := False; exit;
    end;
    if IsLoopbackAddress(DbHost) then begin
      MsgBox('In Internal Server Mode the address cannot be localhost or 127.0.0.1. Enter the network hostname or IP of the PostgreSQL server, or go back and choose Local Mode.', mbError, MB_OK);
      Result := False; exit;
    end;
    if (PortNum < 1) or (PortNum > 65535) then begin
      MsgBox('Port must be between 1 and 65535.', mbError, MB_OK); Result := False; exit;
    end;
    if DbName = '' then begin
      MsgBox('Database name is required.', mbError, MB_OK); Result := False; exit;
    end;
    if DbUser = '' then begin
      MsgBox('Username is required.', mbError, MB_OK); Result := False; exit;
    end;
    if DbPass = '' then begin
      MsgBox('Password is required.', mbError, MB_OK); Result := False; exit;
    end;
    if (DbSslMode <> 'disable') and (DbSslMode <> 'prefer') and (DbSslMode <> 'require')
       and (DbSslMode <> 'allow') and (DbSslMode <> 'verify-ca') and (DbSslMode <> 'verify-full') then begin
      MsgBox('SSL mode must be one of: disable, prefer, require (or allow / verify-ca / verify-full).', mbError, MB_OK);
      Result := False; exit;
    end;
    DbPort := PortNum;

    { Pre-flight connection test against the maintenance database so the user
      gets a clear error before the install begins. }
    PwFile := ExpandConstant('{tmp}\pgpass.txt');
    if not SaveStringToFile(PwFile, DbPass, False) then begin
      MsgBox('Could not create a temporary file to test the connection.', mbError, MB_OK);
      Result := False; exit;
    end;
    WizardForm.StatusLabel.Caption := 'Testing the PostgreSQL connection...';
    Code := RunConfigLogged('preflight-test',
      'test-db --host "' + DbHost + '" --port ' + IntToStr(DbPort) +
      ' --db postgres --user "' + DbUser + '" --password-file "' + PwFile +
      '" --sslmode ' + DbSslMode);
    DeleteFile(PwFile);
    if Code <> 0 then begin
      MsgBox('Could not connect to the PostgreSQL server at ' + DbHost + ':' + IntToStr(DbPort) + '.' + #13#10 +
             'Please check that:' + #13#10 +
             '  - the server is reachable on the network and the port is open,' + #13#10 +
             '  - the username and password are correct,' + #13#10 +
             '  - PostgreSQL is running and accepts connections.' + #13#10 + #13#10 +
             'Details were written to the installer log under ' + ExpandConstant('{commonappdata}\PHASEINV2\logs') + '.',
             mbError, MB_OK);
      Result := False; exit;
    end;
    exit;
  end;
end;

{ ---- PostgreSQL detection (informational only) ----
  Setup does not install PostgreSQL; the customer installs it manually. These
  helpers only make the install log easier to read - they record whether an
  engine was present on the machine at all. }

function PostgreSQLRootLooksInstalled(Root: String): Boolean;
var
  FindRec: TFindRec;
  Candidate: String;
begin
  Result := False;
  if not DirExists(Root) then
    exit;
  if FindFirst(Root + '\*', FindRec) then begin
    try
      repeat
        if ((FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
           (FindRec.Name <> '.') and (FindRec.Name <> '..') then begin
          Candidate := Root + '\' + FindRec.Name;
          if FileExists(Candidate + '\bin\psql.exe') then begin
            Result := True;
            exit;
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function PostgreSQLLooksInstalled: Boolean;
begin
  Result := PostgreSQLRootLooksInstalled(ExpandConstant('{commonpf}\PostgreSQL'));
  if not Result then
    Result := PostgreSQLRootLooksInstalled(ExpandConstant('{commonpf32}\PostgreSQL'));
end;

procedure LogPostgreSQLPresence;
begin
  if PostgreSQLLooksInstalled then
    AppendInstallLog('PostgreSQL detected in Program Files (installed manually, as intended).')
  else
    AppendInstallLog('NOTE: no PostgreSQL found under Program Files. If Local Mode was chosen, ' +
                     'it must be installed manually; the connection test below reports the outcome.');
end;

procedure BackupExistingProfile;
var
  BackupName: String;
begin
  if FileExists(ProfilePath) then begin
    BackupName := ProfilePath + '.bak-' + GetDateTimeString('yyyymmdd-hhnnss', #0, #0);
    if CopyFile(ProfilePath, BackupName, False) then
      AppendInstallLog('Existing connection profile backed up to ' + BackupName + '.');
  end;
end;

function RunConfigLoggedRetry(StepName, Args: String; Attempts: Integer): Integer;
var
  I, Code: Integer;
begin
  Code := -1;
  for I := 1 to Attempts do begin
    Code := RunConfigLogged(StepName + '#' + IntToStr(I), Args);
    if Code = 0 then begin
      Result := 0;
      exit;
    end;
    if I < Attempts then
      Sleep(3000);
  end;
  Result := Code;
end;

procedure WarnContinue(Msg: String);
begin
  AppendInstallLog('WARNING: ' + Msg);
  MsgBox(Msg, mbError, MB_OK);
end;

{ Record the chosen backup folder for the application. The JSON merge/escaping is
  done by the config helper in Python, so a re-install cannot reset the customer's
  other backup settings. Declared after WarnContinue/RunConfigLogged because
  Pascal Script resolves identifiers in file order. }
procedure ConfigureBackupFolder;
var
  Folder, BackupArg, SettingsPath: String;
  Code, TrailSlashes: Integer;
begin
  Folder := GetBackupDir('');
  SettingsPath := ExpandConstant('{commonappdata}\PHASEINV2\backup_settings.json');
  { A path ending in a backslash (e.g. a drive root like "F:\") breaks command-line
    quoting: the trailing \" is parsed as an escaped quote and swallows --out.
    Double every trailing backslash so the closing quote stays literal. }
  BackupArg := Folder;
  TrailSlashes := 0;
  while (Length(BackupArg) - TrailSlashes > 0) and
        (BackupArg[Length(BackupArg) - TrailSlashes] = '\') do
    TrailSlashes := TrailSlashes + 1;
  while TrailSlashes > 0 do
  begin
    BackupArg := BackupArg + '\';
    TrailSlashes := TrailSlashes - 1;
  end;
  Code := RunConfigLogged('set-backup-dir',
    'set-backup-dir --path "' + BackupArg + '" --out "' + SettingsPath + '"');
  if Code = 0 then
    AppendInstallLog('Automatic backups will be written to ' + Folder + '.')
  else
    WarnContinue('Could not record the backup folder "' + Folder + '".' + #13#10 +
                 'The application will use its default folder (' +
                 ExpandConstant('{commonappdata}\PHASEINV2\Backups') + ') instead.');
end;

{ Database setup is resilient: it always installs the app and writes the intended
  connection profile, tests the connection with retries (a freshly-started
  PostgreSQL service can take a few seconds to accept connections), and on any
  database problem it WARNS clearly and continues rather than aborting. The app's
  first-run connection screen + idempotent schema provisioning complete anything
  deferred here on first launch. }
procedure DoDatabaseSetup;
var
  PwFile, CommonArgs, LogsDir: String;
  Code: Integer;
begin
  LogFile := ExpandConstant('{commonappdata}\PHASEINV2\logs\install-' +
                            GetDateTimeString('yyyymmdd-hhnnss', #0, #0) + '.log');
  LogsDir := ExpandConstant('{commonappdata}\PHASEINV2\logs');
  AppendInstallLog('=== PHASEINV2 setup started (v{#MyAppVersion}) ===');
  AppendInstallLog('Mode=' + ModeName + '  InstallDir=' + ExpandConstant('{app}'));

  PwFile := ExpandConstant('{tmp}\pgpass.txt');
  if not SaveStringToFile(PwFile, DbPass, False) then
    RaiseException('Could not write the temporary PostgreSQL password file.');

  if IsLocalMode then
    DbHost := '127.0.0.1';
  LogPostgreSQLPresence;
  ConfigureBackupFolder;

  AppendInstallLog('Host=' + DbHost + '  Port=' + IntToStr(DbPort) +
                   '  Db=' + DbName + '  User=' + DbUser + '  Ssl=' + DbSslMode +
                   '  (password not logged)');

  CommonArgs := ' --host "' + DbHost + '" --port ' + IntToStr(DbPort) +
                ' --user "' + DbUser + '" --password-file "' + PwFile +
                '" --sslmode ' + DbSslMode;

  { Always write the connection profile so the app knows the intended settings
    even if the DB is not reachable during setup. }
  BackupExistingProfile;
  Code := RunConfigLogged('write-profile',
    'write --mode lan --address "' + DbHost + '" --port ' + IntToStr(DbPort) +
    ' --db "' + DbName + '" --user "' + DbUser + '" --password-file "' + PwFile +
    '" --sslmode ' + DbSslMode + ' --out "' + ProfilePath + '"');
  if Code = 0 then
    AppendInstallLog('Connection profile written to ' + ProfilePath + '.')
  else
    WarnContinue('Could not write the connection profile to ' + ProfilePath +
                 '. You can configure the connection from within the application on first launch.');

  { Connection test with retries. }
  Code := RunConfigLoggedRetry('connection-test', 'test-db --db postgres' + CommonArgs, 6);
  if Code <> 0 then begin
    DeleteFile(PwFile);
    WarnContinue('The database connection could not be verified.' + #13#10 +
                 'Setup will finish and install the application. On first launch the application will let you verify the connection and will create the schema automatically.' + #13#10 +
                 'Check the server address, port, username, password, and that PostgreSQL is running. Details: ' + LogsDir + '.');
    AppendInstallLog('Connection not verified; DB creation/provisioning deferred to first application launch.');
    exit;
  end;

  { Create the application database only if it is missing (never dropped). }
  Code := RunConfigLogged('create-db', 'create-db --db "' + DbName + '"' + CommonArgs + ' --maintenance-db postgres');
  if Code <> 0 then begin
    DeleteFile(PwFile);
    WarnContinue('Could not create or access the database "' + DbName +
                 '". The account may lack CREATE DATABASE permission. The application will attempt to use it on first launch. See ' + LogsDir + '.');
    exit;
  end;

  { Provision schema + seed admin/roles/permissions idempotently. }
  Code := RunConfigLogged('provision', 'provision --db "' + DbName + '"' + CommonArgs);
  DeleteFile(PwFile);
  if Code <> 0 then begin
    WarnContinue('Database schema initialization did not complete during setup. The application will complete it automatically on first launch. See ' + LogsDir + '.');
    exit;
  end;

  AppendInstallLog('Database setup completed successfully.');
end;

procedure CopySetupLogToDataDir;
var
  Dest: String;
begin
  Dest := ExpandConstant('{commonappdata}\PHASEINV2\logs\setup-' +
                         GetDateTimeString('yyyymmdd-hhnnss', #0, #0) + '.log');
  CopyFile(ExpandConstant('{log}'), Dest, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    DoDatabaseSetup;
  if CurStep = ssDone then begin
    AppendInstallLog('Shortcuts created. Desktop shortcut: ' + IntToStr(Ord(WizardIsTaskSelected('desktopicon'))) + ' (1=yes).');
    AppendInstallLog('=== PHASEINV2 setup completed ===');
    CopySetupLogToDataDir;
  end;
end;
