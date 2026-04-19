# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Hidden imports for FastAPI ecosystem
hidden_imports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'pydantic',
    'pydantic_core',
    'starlette',
    # Application modules
    'src',
    'src.main',
    'src.models',
    'src.models.requests',
    'src.models.responses',
    'src.services',
    'src.services.transcription',
    'src.services.gpu_manager',
    'src.services.audio_processor',
    'src.utils',
    'src.utils.security',
    'src.utils.validation',
    'src.services.youtube_downloader',
    'yt_dlp',
]

# Add faster-whisper and its dependencies
# NOTE: faster-whisper uses ctranslate2 (C++ library), NOT torch
# We DO NOT include torch here - it's only used for device detection
# which we've replaced with subprocess calls (saves 250MB)
hidden_imports += collect_submodules('faster_whisper')
hidden_imports += collect_submodules('yt_dlp')

# Collect data files
datas = []
datas += collect_data_files('faster_whisper')

# Include the entire src directory as data
datas += [('src', 'src')]

a = Analysis(
    ['backend_main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce bundle size
        'matplotlib',
        'PIL',
        'tkinter',
        'IPython',
        'notebook',
        'jupyter',
        'torch',  # CRITICAL: Exclude torch - not needed with subprocess GPU detection
        'torchvision',
        'torchaudio',
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
    name='scribble-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',  # Will be set by build script
    codesign_identity=None,
    entitlements_file=None,
)
