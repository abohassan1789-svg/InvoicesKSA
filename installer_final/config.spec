# -*- mode: python ; coding: utf-8 -*-
# Brand-new PyInstaller spec (2026-08-22) for the installer-only config helper.
#
# Produces an *onefile* console executable:  dist\phaseinv2-config.exe
#
# The ``provision`` sub-command reads app/database/schema/full_schema.sql at run
# time (schema_bootstrap resolves it next to its module). A onefile build archives
# the .py into the PYZ but NOT that .sql data file, so it MUST be added explicitly
# at the SAME relative path the code expects, or setup's schema step fails with
# "No such file or directory". PySide6/Qt are excluded: the helper is pure console
# and pulling in Qt would bloat it for nothing.

import os

PROJECT_ROOT = os.path.dirname(SPECPATH)
SCHEMA_SQL = os.path.join(PROJECT_ROOT, 'app', 'database', 'schema', 'full_schema.sql')

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'installer_final', 'entrypoints', 'config_main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[(SCHEMA_SQL, 'app/database/schema')],
    hiddenimports=['app.config.configure_cli'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'shiboken6', 'PySide6.QtWebEngineWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='phaseinv2-config',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
