# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для NTE Fish.

Сборка: запусти build.bat (или вручную:
    venv\\Scripts\\pyinstaller.exe nte_fish.spec --noconfirm)

Результат: dist\\NTE_Fish\\NTE_Fish.exe
"""

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ('icon.ico', '.'),
    ('templates', 'templates'),
]
datas += collect_data_files('customtkinter')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder',
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
    [],
    exclude_binaries=True,
    name='NTE_Fish',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,         # без чёрного консольного окна
    icon='icon.ico',
    uac_admin=True,        # автоматический UAC-запрос на админа при запуске
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NTE_Fish',
)
