# -*- mode: python ; coding: utf-8 -*-

from app import __version__

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/template.pdf', 'assets'), ('assets/icon.icns', 'assets'), ('assets/fonts', 'assets/fonts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Polecenie przelewu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Polecenie przelewu',
)
app = BUNDLE(
    coll,
    name='Polecenie przelewu.app',
    icon='assets/icon.icns',
    bundle_identifier='pl.polecenieprzelewu.desktop',
    info_plist={
        'CFBundleShortVersionString': __version__,
        'CFBundleVersion': __version__,
    },
)
