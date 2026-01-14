# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for AWS End-of-Support Tool."""

import os
import sys

block_cipher = None

# Get the path to the templates directory
templates_path = os.path.join('src', 'templates')

a = Analysis(
    ['src/gui.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # Include the pivot template
        (os.path.join(templates_path, 'pivot_template.xlsx'), 'src/templates'),
        # Include all source files
        ('src/models.py', '.'),
        ('src/parser.py', '.'),
        ('src/classifier.py', '.'),
        ('src/generator.py', '.'),
        ('src/formatters.py', '.'),
    ],
    hiddenimports=[
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.workbook',
        'openpyxl.worksheet',
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
    name='EndOfSupportTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)
