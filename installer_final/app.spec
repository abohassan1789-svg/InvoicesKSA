# -*- mode: python ; coding: utf-8 -*-
# Brand-new PyInstaller spec (2026-08-22) for the PHASEINV2 main-device GUI app.
#
# Produces an *onedir* windowed bundle:  dist\PHASEINV2\PHASEINV2.exe
#
# Why the ``app`` package is collected as 'pyz+py' (both archived AND written to
# disk as real .py files under _internal\app): the invoice assets and the SQL
# migrations/schema are bundled under ``app\...`` as DATA. If ``app`` lived only
# in the PYZ archive, that _internal\app data directory would shadow it at import
# time (a namespace package with no modules) and the app would die with
# "No module named 'app.main'". Collecting ``app`` as files makes _internal\app a
# real importable package that ALSO carries the data. This is what guarantees
# today's new print templates (v9/v10/v11 + phase-1) are importable at runtime.

import os
from PyInstaller.utils.hooks import collect_submodules

# SPECPATH is injected by PyInstaller and points at this file's directory
# (installer_final). The project root is its parent (CRM_PYTHON_APP_STRUCTURE).
PROJECT_ROOT = os.path.dirname(SPECPATH)

# collect_submodules('app') pulls in EVERY app.* module (including modules that
# are only imported lazily inside button handlers, e.g. the print templates), so
# nothing added today can be silently left out of the bundle.
hiddenimports = collect_submodules('app') + [
    'reportlab', 'qrcode', 'num2words', 'arabic_reshaper', 'bidi',
]

# Whole directories bundled as data -> every asset/migration/schema file ships,
# including PNGs added today (mutakamila_logo, alesnad_*, aqaseem_header, ...).
datas = [
    (os.path.join(PROJECT_ROOT, 'app', 'database', 'migrations'), 'app/database/migrations'),
    (os.path.join(PROJECT_ROOT, 'app', 'database', 'schema'), 'app/database/schema'),
    (os.path.join(PROJECT_ROOT, 'app', 'ui', 'assets'), 'app/ui/assets'),
]

app_icon = os.path.join(PROJECT_ROOT, 'app', 'ui', 'assets', 'app_icon.ico')

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'installer_final', 'entrypoints', 'app_main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    module_collection_mode={'app': 'pyz+py'},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PHASEINV2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=(app_icon if os.path.exists(app_icon) else None),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PHASEINV2',
)
