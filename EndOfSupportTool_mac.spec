# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for macOS

import sys
from pathlib import Path

block_cipher = None

# Get the source directory
src_dir = Path('src')

a = Analysis(
    ['src/gui.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=[
        ('src/templates', 'templates'),
    ],
    hiddenimports=[
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'src.parser',
        'src.classifier',
        'src.generator',
        'src.formatters',
        'src.models',
        'parser',
        'classifier',
        'generator',
        'formatters',
        'models',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'win32com',
        'win32api',
        'pythoncom',
        'pywintypes',
        'pywin32',
    ],
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
    name='EndOfSupportTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Important for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Create macOS .app bundle
app = BUNDLE(
    exe,
    name='EndOfSupportTool.app',
    icon=None,  # Add icon path here if you have one (e.g., 'icon.icns')
    bundle_identifier='com.endofsupport.tool',
    info_plist={
        'CFBundleName': 'EndOfSupportTool',
        'CFBundleDisplayName': 'AWS End-of-Support Tool',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
    },
)
