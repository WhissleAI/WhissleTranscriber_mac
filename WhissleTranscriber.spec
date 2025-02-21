# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app_demo.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.')],  # Include logo.png in the bundle
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'google',
        'google.auth',
        'google.oauth2',
        'google_auth_oauthlib',
        'googleapiclient'
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
    [],
    exclude_binaries=True,
    name='WhissleTranscriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WhissleTranscriber',
)

app = BUNDLE(
    coll,
    name='WhissleTranscriber.app',
    icon=None,
    bundle_identifier=None,
) 