# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\gui.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=['classifier', 'models', 'formatters', 'html_formatter', 'extended_support_lookup', 'eks_insights', 'ai_summary'],
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
    a.binaries,
    a.datas,
    [],
    name='EndOfSupportTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
