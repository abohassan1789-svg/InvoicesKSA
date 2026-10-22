<#
    build.ps1 - one-command build of the FINAL PHASEINV2 installer (2026-08-22).

    Brand-new, self-contained build. It produces a single ready-to-ship setup
    executable from TODAY's application code:

        D:\PHASEINV2\dist\PHASEINV2_Setup.exe

    Steps:
      1. Locate Python 3.11 and Inno Setup 6.
      2. Clean this build's previous output (dist / build / Output only).
      3. Create/reuse an isolated build virtualenv + install requirements + PyInstaller.
      4. Freeze the GUI app       -> dist\PHASEINV2\PHASEINV2.exe   (onedir, windowed).
      5. Freeze the config helper  -> dist\phaseinv2-config.exe      (onefile, console).
      6. Validate the frozen bundle (libraries, Qt, assets, today's templates) + smoke test.
      7. Compile setup.iss with Inno Setup 6.
      8. Copy the final installer to D:\PHASEINV2\dist and print path/size/SHA-256.

    The database password is never handled here - it is entered by the user at
    install time only.

    IMPORTANT (PowerShell 5.1): do NOT pipe this script through `2>&1`. PyInstaller
    logs INFO to stderr; the redirect turns every line into a NativeCommandError
    and the build reports failure while actually succeeding. Just run:
        .\installer_final\build.ps1
#>
[CmdletBinding()]
param(
    [string]$InnoCompiler = '',
    [string]$PythonExe = ''
)

$ErrorActionPreference = 'Stop'

function Write-Step($m) { Write-Host "[..] $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function Write-Err($m)  { Write-Host "[!!] $m" -ForegroundColor Red }

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path   # ...\installer_final
$ProjectRoot  = Split-Path -Parent $InstallerDir                  # ...\CRM_PYTHON_APP_STRUCTURE
$RepoRoot     = Split-Path -Parent $ProjectRoot                   # D:\PHASEINV2
$VenvDir      = Join-Path $InstallerDir '.buildvenv'
$DistDir      = Join-Path $InstallerDir 'dist'
$BuildDir     = Join-Path $InstallerDir 'build'
$OutputDir    = Join-Path $InstallerDir 'Output'
$IssPath      = Join-Path $InstallerDir 'setup.iss'
$AppSpec      = Join-Path $InstallerDir 'app.spec'
$ConfigSpec   = Join-Path $InstallerDir 'config.spec'
$FinalName    = 'PHASEINV2_Setup.exe'
$FinalDistDir = Join-Path $RepoRoot 'dist'
$FinalPath    = Join-Path $FinalDistDir $FinalName

# --- input validation -------------------------------------------------------
foreach ($f in @($IssPath, $AppSpec, $ConfigSpec)) {
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

# --- 1) clean ---------------------------------------------------------------
Write-Step 'Cleaning previous build output'
foreach ($d in @($DistDir, $BuildDir, $OutputDir)) {
    if (Test-Path $d) { Remove-Item -Recurse -Force $d }
}
New-Item -ItemType Directory -Force -Path $DistDir, $OutputDir, $FinalDistDir | Out-Null

# --- 2) build venv ----------------------------------------------------------
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

# --- 3) freeze the GUI app --------------------------------------------------
Write-Step 'Freezing PHASEINV2.exe (GUI, onedir, from app.spec)'
& $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistDir --workpath $BuildDir $AppSpec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed for PHASEINV2.exe.' }

# --- 4) freeze the config helper -------------------------------------------
Write-Step 'Freezing phaseinv2-config.exe (console, onefile, from config.spec)'
& $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistDir --workpath $BuildDir $ConfigSpec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed for phaseinv2-config.exe.' }

# --- 5) validate frozen inputs ---------------------------------------------
Write-Step 'Validating frozen outputs'
$AppExe    = Join-Path $DistDir 'PHASEINV2\PHASEINV2.exe'
$ConfigExe = Join-Path $DistDir 'phaseinv2-config.exe'
foreach ($f in @($AppExe, $ConfigExe)) {
    if (-not (Test-Path $f)) { throw "Expected build artifact missing: $f" }
}
$internal = Join-Path $DistDir 'PHASEINV2\_internal'
$missing = @()
$checks = [ordered]@{
    'PySide6 runtime'                     = (Test-Path (Join-Path $internal 'PySide6'))
    'Qt platform plugin'                  = (Get-ChildItem -Path $internal -Recurse -Filter 'qwindows.dll' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'QtWebEngine (ZATCA preview/PDF)'     = (Get-ChildItem -Path $internal -Recurse -Filter 'QtWebEngineProcess.exe' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'psycopg driver'                      = (Test-Path (Join-Path $internal 'psycopg')) -or (Get-ChildItem -Path $internal -Recurse -Filter '_psycopg*.pyd' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'cryptography (DPAPI/Fernet)'         = (Test-Path (Join-Path $internal 'cryptography'))
    'migrations bundled'                  = (Get-ChildItem -Path $internal -Recurse -Filter '001_create_core_schema.sql' -ErrorAction SilentlyContinue | Select-Object -First 1)
    'full schema bundled (auto-provision)'= (Test-Path (Join-Path $internal 'app\database\schema\full_schema.sql'))
    'ZATCA assets'                        = (Get-ChildItem -Path $internal -Recurse -Filter 'tax-invoice-title.png' -ErrorAction SilentlyContinue | Select-Object -First 1)
}

# Print templates are imported lazily inside the screens' button handlers, so a
# missing one raises nothing at start-up - it only fails when a user clicks معاينة.
# Each template module is therefore verified as a file. This build's list includes
# TODAY's new templates (v9/v10/v11 + phase-1) so a fresh build cannot ship without them.
# v4.14.0 (2026-10-07): + invoice templates v12..v21, vouchers v10..v12, simplified
# receipt, and the image assets the new fixed-brand / replica templates load at print time.
$screensDir = Join-Path $internal 'app\ui\screens'
$templateModules = @(
    'saudi_invoice_print.py', 'saudi_invoice_print_v2.py', 'saudi_invoice_print_v3.py',
    'saudi_invoice_print_v4.py', 'saudi_invoice_print_v5.py', 'saudi_invoice_print_v6.py',
    'saudi_invoice_print_v7.py', 'saudi_invoice_print_v8.py',
    'saudi_invoice_print_v9.py', 'saudi_invoice_print_v10.py', 'saudi_invoice_print_v11.py',
    'saudi_invoice_print_v12.py', 'saudi_invoice_print_v13.py', 'saudi_invoice_print_v14.py',
    'saudi_invoice_print_v15.py', 'saudi_invoice_print_v16.py', 'saudi_invoice_print_v17.py',
    'saudi_invoice_print_v18.py', 'saudi_invoice_print_v19.py', 'saudi_invoice_print_v20.py',
    'saudi_invoice_print_v21.py', 'saudi_invoice_print_v28.py', 'saudi_invoice_print_v29.py',
    'saudi_invoice_print_v30.py',
    'saudi_invoice_print_phase1.py', 'saudi_voucher_print_phase1.py',
    'saudi_receipt_voucher_print.py', 'saudi_receipt_voucher_print_v10.py',
    'saudi_receipt_voucher_print_v11.py', 'saudi_receipt_voucher_print_v12.py',
    'saudi_simplified_invoice_print.py', 'customer_statement_print.py',
    'cashier_receipt_print.py', 'invoice_pagination.py'
)
foreach ($m in $templateModules) {
    $checks["print template: $m"] = (Test-Path (Join-Path $screensDir $m))
}
$assetsDir = Join-Path $internal 'app\ui\assets\saudi_invoice'
foreach ($a in @('atyaf_header.png', 'atyaf_footer.png', 'riyal_symbol.png', 'mawsim_fruitseason_logo.png',
                  'noto_naskh_arabic_regular.woff2', 'noto_naskh_arabic_bold.woff2',
                  'inter_latin_400.woff2', 'inter_latin_600.woff2', 'inter_latin_700.woff2',
                  'inter_latin_800.woff2')) {
    $checks["print asset: $a"] = (Test-Path (Join-Path $assetsDir $a))
}
foreach ($k in $checks.Keys) {
    if ($checks[$k]) { Write-Ok "bundled: $k" } else { Write-Err "NOT FOUND in bundle: $k"; $missing += $k }
}

# Runtime smoke test: the frozen config helper exercises the packaged app.config
# import stack. If the app package or its pure-Python deps were not archived, it fails.
Write-Step 'Smoke-testing frozen phaseinv2-config.exe'
$smoke = (& $ConfigExe detect-ips | Out-String)
if ($LASTEXITCODE -eq 0 -and $smoke -match '"ok":\s*true') {
    Write-Ok 'frozen config helper runs (app package + deps import OK)'
} else {
    Write-Err "frozen config helper smoke test failed: $smoke"
    $missing += 'frozen app package import'
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
Write-Ok '================= BUILD COMPLETE ================='
Write-Host "Installer path : $FinalPath"
Write-Host "File name      : $FinalName"
Write-Host "File size      : $sizeMB MB ($($item.Length) bytes)"
Write-Host "SHA-256        : $sha"
Write-Host "App exe (after install): {app}\PHASEINV2.exe"
Write-Host "Config profile : C:\ProgramData\PHASEINV2\connection.json"
Write-Host "Install logs   : C:\ProgramData\PHASEINV2\logs"
Write-Ok '================================================='
