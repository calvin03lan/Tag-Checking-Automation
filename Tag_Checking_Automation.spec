# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/calvinlaam/Documents/trae_projects/Tag_Checking_Automation/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='Tag_Checking_Automation',
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
    icon=['/Users/calvinlaam/Documents/trae_projects/Tag_Checking_Automation/TAT.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Tag_Checking_Automation',
)
app = BUNDLE(
    coll,
    name='Tag_Checking_Automation.app',
    icon='/Users/calvinlaam/Documents/trae_projects/Tag_Checking_Automation/TAT.ico',
    bundle_identifier='com.hangseng.tagcheckingautomation',
)
