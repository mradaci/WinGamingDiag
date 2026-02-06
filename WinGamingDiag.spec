# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'src.core.agent',
        'src.collectors.hardware',
        'src.collectors.event_logs',
        'src.collectors.drivers',
        'src.collectors.launchers',
        'src.collectors.network',
        'src.models',
        'src.utils.cli',
        'src.utils.wmi_helper',
        'src.utils.redaction',
        'src.utils.history',
        'src.utils.updater',
        'src.utils.benchmark',
        'src.core.rules',
        'src.reports.html_generator',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WinGamingDiag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)