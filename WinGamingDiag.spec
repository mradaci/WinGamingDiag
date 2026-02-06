# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Analysis for the main application
main_app = Analysis(
    ['__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(main_app.pure, main_app.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    main_app.scripts,
    [],
    exclude_binaries=True,
    name='WinGamingDiag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

# We don't need a separate EXE for the collector, it's a pyz.
# The main exe can run it. This simplifies things.
# We just need to ensure all its dependencies are found.

coll = COLLECT(
    exe,
    main_app.binaries,
    main_app.zipfiles,
    main_app.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WinGamingDiag',
)
