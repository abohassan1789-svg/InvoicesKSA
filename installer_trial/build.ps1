<#
    build.ps1 - one-command build of the PHASEINV2 TRIAL installer (2026-08-26).

    Produces a single, ready-to-ship setup executable that needs NOTHING
    pre-installed on the customer's machine (no Python, no PostgreSQL):

        D:\PHASEINV2\dist\PHASEINV2_TRIAL_Setup.exe

    Steps:
      1. Locate Python 3.11, Inno Setup 6, and a source PostgreSQL install.
      2. Assemble a PORTABLE PostgreSQL payload (bin/lib/share + VC++ runtime)
         under installer_trial\payload\pgsql.
      3. Clean previous output (dist / build / Output only).
      4. Create/reuse an isolated build venv + install requirements + PyInstaller.
      5. Freeze the GUI app (onedir, windowed) WITH the embedded PostgreSQL.
      6. Validate the frozen bundle (Qt, psycopg, embedded PostgreSQL, schema,
         today's print templates).
      7. Compile setup.iss with Inno Setup 6.
      8. Copy the final installer to D:\PHASEINV2\dist and print path/size/SHA-256.

    IMPORTANT (PowerShell 5.1): do NOT pipe this script through `2>&1`.
    PyInstaller logs INFO to stderr; the redirect turns every line into a
    NativeCommandError and the build reports failure while actually succeeding.
    Just run:  .\installer_trial\build.ps1
#>
[CmdletBinding()]
param(
    [string]$InnoCompiler = '',
    [string]$PythonExe = '',
    [string]$PgSource = '',        # e.g. 'C:\Program Files\PostgreSQL\18'
    [switch]$RefreshPg             # re-copy the PostgreSQL payload even if present
)

$ErrorActionPreference = 'Stop'

function Write-Step($m) { Write-Host "[..] $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function Write-Err($m)  { Write-Host "[!!] $m" -ForegroundColor Red }

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path   # ...\installer_trial
$ProjectRoot  = Split-Path -Parent $InstallerDir                  # ...\CRM_PYTHON_APP_STRUCTURE
$RepoRoot     = Split-Path -Parent $ProjectRoot                   # D:\PHASEINV2
$VenvDir      = Join-Path $InstallerDir '.buildvenv'
$DistDir      = Join-Path $InstallerDir 'dist'
$BuildDir     = Join-Path $InstallerDir 'build'
$OutputDir    = Join-Path $InstallerDir 'Output'
$PayloadDir   = Join-Path $InstallerDir 'payload'
$PgPayload    = Join-Path $PayloadDir 'pgsql'
$IssPath      = Join-Path $InstallerDir 'setup.iss'
$AppSpec      = Join-Path $InstallerDir 'app.spec'
$FinalName    = 'PHASEINV2_TRIAL_Setup.exe'
$FinalDistDir = Join-Path $RepoRoot 'dist'
$FinalPath    = Join-Path $FinalDistDir $FinalName

foreach ($f in @($IssPath, $AppSpec)) {
    if (-not (Test-Path $f)) { throw "Missing build input: $f" }
}

# --- locate Python ----------------------------------------------------------
if (-not $PythonExe) {
    $known = 'C:\Users\hp\AppData\Local\Programs\Python\Python311\python.exe'
    if (Test-Path $known) { $PythonExe = $known }
}
if (-not $PythonExe) {
    $pyLauncher = (Get-Command py.exe -ErrorAction SilentlyContinue)
    if ($pyLauncher) {
        $probe = & $pyLauncher.Source -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe) { $PythonExe = $probe.Trim() }
    }
}
if (-not $PythonExe) { $PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
if (-not $PythonExe) { throw 'Python 3.11 was not found. Pass -PythonExe <path>.' }
Write-Ok "Python: $PythonExe"

# --- locate Inno Setup ------------------------------------------------------
if (-not $InnoCompiler) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { $InnoCompiler = $c; break } }
}
if (-not (Test-Path $InnoCompiler)) { throw "Inno Setup compiler (ISCC.exe) not found. Pass -InnoCompiler <path>." }
Write-Ok "Inno Setup: $InnoCompiler"

# --- locate a source PostgreSQL install -------------------------------------
if (-not $PgSource) {
    $roots = @("$env:ProgramFiles\PostgreSQL", "${env:ProgramFiles(x86)}\PostgreSQL")
    $best = $null; $bestVer = -1
    foreach ($root in $roots) {
        if (Test-Path $root) {
            Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                if (Test-Path (Join-Path $_.FullName 'bin\postgres.exe')) {
                    $v = 0; [int]::TryParse($_.Name, [ref]$v) | Out-Null
                    if ($v -gt $bestVer) { $bestVer = $v; $best = $_.FullName }
                }
            }
        }
    }
    $PgSource = $best
}
if (-not $PgSource -or -not (Test-Path (Join-Path $PgSource 'bin\postgres.exe'))) {
    throw "No source PostgreSQL install found. Pass -PgSource 'C:\Program Files\PostgreSQL\<ver>'."
}
Write-Ok "PostgreSQL source: $PgSource"

# --- 1) assemble the portable PostgreSQL payload ----------------------------
if ($RefreshPg -and (Test-Path $PgPayload)) { Remove-Item -Recurse -Force $PgPayload }
if (-not (Test-Path (Join-Path $PgPayload 'bin\postgres.exe'))) {
    Write-Step "Assembling portable PostgreSQL payload from $PgSource"
    New-Item -ItemType Directory -Force -Path $PgPayload | Out-Null
    foreach ($sub in @('bin', 'lib', 'share')) {
        $src = Join-Path $PgSource $sub
        if (-not (Test-Path $src)) { throw "Source PostgreSQL is missing '$sub': $src" }
        Copy-Item -Recurse -Force $src (Join-Path $PgPayload $sub)
    }

    # Trim client/GUI tooling the embedded SERVER never needs (keeps size down).
    # Keep: postgres, pg_ctl, initdb, psql, pg_dump(all), pg_isready, pg_restore.
    $binDir = Join-Path $PgPayload 'bin'
    $keepExe = @('postgres.exe','pg_ctl.exe','initdb.exe','psql.exe',
                 'pg_dump.exe','pg_dumpall.exe','pg_restore.exe','pg_isready.exe',
                 'postmaster.exe')
    Get-ChildItem $binDir -Filter *.exe -ErrorAction SilentlyContinue | ForEach-Object {
        if ($keepExe -notcontains $_.Name.ToLower()) { Remove-Item -Force $_.FullName }
    }
    # StackBuilder / wxWidgets / curl DLLs are only used by GUI client tools.
    foreach ($pat in @('wx*.dll','libcurl.dll','testplug.dll')) {
        Get-ChildItem $binDir -Filter $pat -ErrorAction SilentlyContinue | Remove-Item -Force
    }

    # App-local VC++ runtime so postgres.exe runs on a machine without the
    # Microsoft Visual C++ Redistributable installed.
    $sys32 = Join-Path $env:WINDIR 'System32'
    foreach ($dll in @('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll')) {
        $src = Join-Path $sys32 $dll
        if (Test-Path $src) { Copy-Item -Force $src (Join-Path $binDir $dll) }
        else { Write-Err "VC++ runtime DLL not found: $src (postgres.exe may fail on a clean PC)" }
    }
    Write-Ok "Portable PostgreSQL payload ready: $PgPayload"
} else {
    Write-Ok "Reusing existing PostgreSQL payload (pass -RefreshPg to rebuild it): $PgPayload"
}
$env:PHASEINV2_PG_PAYLOAD = $PgPayload

# --- 2) clean ---------------------------------------------------------------
Write-Step 'Cleaning previous build output'
foreach ($d in @($DistDir, $BuildDir, $OutputDir)) {
    if (Test-Path $d) { Remove-Item -Recurse -Force $d }
}
New-Item -ItemType Directory -Force -Path $DistDir, $OutputDir, $FinalDistDir | Out-Null

# --- 3) build venv ----------------------------------------------------------
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$venvOk = $false
if (Test-Path $VenvPython) {
    & $VenvPython -c "import encodings" 2>$null
    if ($LASTEXITCODE -eq 0) { $venvOk = $true }
}
if (-not $venvOk) {
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
    Write-Step 'Creating build virtual environment'
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the build virtual environment.' }
    $VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
}

Write-Step 'Installing build dependencies (requirements.txt + PyInstaller)'
& $VenvPython -m pip install --upgrade pip | Out-Null
& $VenvPython -m pip install -r (Join-Path $ProjectRoot 'requirements.txt') pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

# --- 4) freeze the GUI app (with embedded PostgreSQL) -----------------------
Write-Step 'Freezing PHASEINV2.exe (GUI, onedir, embedded PostgreSQL)'
& $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistDir --workpath $BuildDir $AppSpec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed for PHASEINV2.exe.' }

# --- 5) validate frozen outputs ---------------------------------------------
Write-Step 'Validating frozen outputs'
$AppExe   = Join-Path $DistDir 'PHASEINV2\PHASEINV2.exe'
if (-not (Test-Path $AppExe)) { throw "Expected build artifact missing: $AppExe" }
$internal = Join-Path $DistDir 'PHASEINV2\_internal'
$pgbin    = Join-Path $internal 'pgsql\bin'
$missing = @()
$checks = [ordered]@{
    'PySide6 runtime'                     = (Test-Path (Join-Path $internal 'PySide6'))
    'Qt platform plugin'                  = (Get-ChildItem -Path $internal -Recurse -Filter 'qwindows.dll' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'QtWebEngine (ZATCA preview/PDF)'     = (Get-ChildItem -Path $internal -Recurse -Filter 'QtWebEngineProcess.exe' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'psycopg driver'                      = (Test-Path (Join-Path $internal 'psycopg')) -or (Get-ChildItem -Path $internal -Recurse -Filter '_psycopg*.pyd' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'cryptography (DPAPI/Fernet)'         = (Test-Path (Join-Path $internal 'cryptography'))
    'full schema bundled (auto-provision)'= (Test-Path (Join-Path $internal 'app\database\schema\full_schema.sql'))
    'embedded postgres.exe'               = (Test-Path (Join-Path $pgbin 'postgres.exe'))
    'embedded initdb.exe'                 = (Test-Path (Join-Path $pgbin 'initdb.exe'))
    'embedded pg_ctl.exe'                 = (Test-Path (Join-Path $pgbin 'pg_ctl.exe'))
    'embedded pg_dump.exe (backups)'      = (Test-Path (Join-Path $pgbin 'pg_dump.exe'))
    'embedded libpq.dll'                  = (Test-Path (Join-Path $pgbin 'libpq.dll'))
    'embedded VC++ runtime'               = (Test-Path (Join-Path $pgbin 'vcruntime140.dll'))
    'embedded share (initdb data)'        = (Test-Path (Join-Path $internal 'pgsql\share\postgres.bki'))
    'trial guard module'                  = (Test-Path (Join-Path $internal 'app\security\trial_guard.py'))
    'embedded pg manager module'          = (Test-Path (Join-Path $internal 'app\services\embedded_postgres.py'))
}
$screensDir = Join-Path $internal 'app\ui\screens'
$templateModules = @(
    'saudi_invoice_print.py', 'saudi_invoice_print_v2.py', 'saudi_invoice_print_v3.py',
    'saudi_invoice_print_v4.py', 'saudi_invoice_print_v5.py', 'saudi_invoice_print_v6.py',
    'saudi_invoice_print_v7.py', 'saudi_invoice_print_v8.py',
    'saudi_invoice_print_v9.py', 'saudi_invoice_print_v10.py', 'saudi_invoice_print_v11.py',
    'saudi_invoice_print_phase1.py', 'saudi_voucher_print_phase1.py',
    'saudi_receipt_voucher_print.py', 'customer_statement_print.py',
    'cashier_receipt_print.py', 'invoice_pagination.py'
)
foreach ($m in $templateModules) {
    $checks["print template: $m"] = (Test-Path (Join-Path $screensDir $m))
}
foreach ($k in $checks.Keys) {
    if ($checks[$k]) { Write-Ok "bundled: $k" } else { Write-Err "NOT FOUND in bundle: $k"; $missing += $k }
}
if ($missing.Count -gt 0) { throw "Build is missing required runtime components: $($missing -join ', ')" }

# --- 6) compile the installer ----------------------------------------------
Write-Step 'Compiling the Inno Setup installer'
& $InnoCompiler $IssPath
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }

$CompiledExe = Join-Path $OutputDir $FinalName
if (-not (Test-Path $CompiledExe)) { throw "Installer was not produced: $CompiledExe" }

# --- 7) copy to the final destination --------------------------------------
Copy-Item -Force $CompiledExe $FinalPath
if (-not (Test-Path $FinalPath)) { throw "Final installer missing: $FinalPath" }

# --- 8) report --------------------------------------------------------------
$item = Get-Item $FinalPath
$sizeMB = [Math]::Round($item.Length / 1MB, 2)
$sha = (Get-FileHash -Algorithm SHA256 $FinalPath).Hash

Write-Host ''
Write-Ok '================= TRIAL BUILD COMPLETE ================='
Write-Host "Installer path : $FinalPath"
Write-Host "File name      : $FinalName"
Write-Host "File size      : $sizeMB MB ($($item.Length) bytes)"
Write-Host "SHA-256        : $sha"
Write-Host "App exe (after install): {app}\PHASEINV2.exe"
Write-Host "Embedded DB     : 127.0.0.1:55432  (data in C:\ProgramData\PHASEINV2_Trial\pgdata)"
Write-Host "Trial policy    : 7 days OR 40 launches"
Write-Ok '======================================================='
