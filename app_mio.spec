# -*- mode: python ; coding: utf-8 -*-
"""
app_mio.spec — Configuración PyInstaller para APP MIO (modo one-directory).

Genera dist/APP MIO/ con el ejecutable y todos los recursos.

Build:
    py -3.12 -m PyInstaller --clean app_mio.spec
  o bien:
    py -3.12 build_desktop.py
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Data files ────────────────────────────────────────────────────────────────
# Formato: ('origen_en_proyecto', 'destino_en_bundle')
datas = [
    # Plantillas Jinja2
    ('app/templates',   'app/templates'),
    # Archivos estáticos (CSS, JS, iconos, manifest)
    ('app/static',      'app/static'),
    # Scripts de migración Alembic
    ('migrations',      'migrations'),
    # Configuración Alembic
    ('alembic.ini',     '.'),
    # Plantilla de configuración para el usuario final
    ('.env.example',    '.'),
]

# Incluir assets internos de pywebview (HTML/JS del frame nativo)
datas += collect_data_files('webview')

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    # --- uvicorn ---
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.middleware',
    'uvicorn.middleware.proxy_headers',
    # --- h11 (HTTP/1.1 para uvicorn) ---
    'h11',
    'h11._readers',
    'h11._writers',
    # --- anyio ---
    'anyio',
    'anyio._backends._asyncio',
    # --- FastAPI / Starlette ---
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.requests',
    'starlette.responses',
    'starlette.staticfiles',
    'starlette.templating',
    'starlette.middleware',
    'starlette.middleware.base',
    'starlette.middleware.cors',
    'starlette.middleware.sessions',
    # --- Pydantic ---
    'pydantic',
    'pydantic.v1',
    'pydantic_settings',
    'pydantic.networks',
    'pydantic.types',
    # --- SQLAlchemy ---
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.dialects',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.sqlite.pysqlite',
    'sqlalchemy.ext.asyncio',
    'sqlalchemy.pool',
    'sqlalchemy.sql.sqltypes',
    # --- Alembic ---
    'alembic',
    'alembic.runtime',
    'alembic.runtime.migration',
    'alembic.operations',
    'alembic.operations.base',
    'alembic.operations.ops',
    'alembic.script',
    'alembic.script.revision',
    'alembic.ddl',
    'alembic.ddl.impl',
    # --- Mako (usado internamente por Alembic) ---
    'mako',
    'mako.template',
    'mako.lookup',
    'mako.runtime',
    # --- Jinja2 ---
    'jinja2',
    'jinja2.ext',
    'jinja2.loaders',
    # --- Autenticación / seguridad ---
    'bcrypt',
    'itsdangerous',
    'itsdangerous.url_safe',
    'itsdangerous.timed',
    # --- Rate limiting ---
    'slowapi',
    'slowapi.middleware',
    # --- Formularios / uploads ---
    'multipart',
    'python_multipart',
    # --- HTTP client ---
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    # --- Email / SMTP ---
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'smtplib',
    # --- Twilio ---
    'twilio',
    'twilio.rest',
    'twilio.http',
    # --- Módulos de la app (importaciones dinámicas) ---
    'app',
    'app.config',
    'app.db',
    'app.main',
    'app.dependencies',
    'app.models',
    'app.models.admin',
    'app.models.app_settings',
    'app.models.backup',
    'app.models.bank_account',
    'app.models.document',
    'app.models.invitation',
    'app.models.payroll',
    'app.models.person',
    'app.models.user',
    'app.models.wallet_address',
    'app.routers.api.documents',
    'app.routers.api.payrolls',
    'app.routers.api.people',
    'app.routers.password_recovery',
    'app.routers.portal',
    'app.routers.public_forms',
    'app.routers.user_auth',
    'app.routers.web.admin_settings',
    'app.routers.web.admin_users',
    'app.routers.web.backups',
    'app.routers.web.pages',
    'app.schemas.document',
    'app.schemas.payroll',
    'app.schemas.person',
    'app.security.auth',
    'app.security.logging',
    'app.security.middleware',
    'app.security.rate_limiter',
    'app.security.user_auth',
    'app.services.backup_service',
    'app.services.document_service',
    'app.services.email_service',
    'app.services.payroll_service',
    'app.services.person_service',
    'app.services.sms_service',
    'app.services.storage_service',
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Excluir paquetes grandes que no usa la app para reducir tamaño del bundle
    excludes=[
        'tkinter', '_tkinter',
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'Pillow',
        'cv2', 'sklearn',
        'IPython', 'jupyter',
        'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE (modo one-directory: exclude_binaries=True) ──────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],                      # sin binarios inline (van al COLLECT)
    exclude_binaries=True,   # obligatorio para one-directory
    name='APP MIO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # sin ventana de consola negra
    icon='app_icon.ico',     # ícono del .exe en el Explorador de Windows
    version=None,
)

# ── COLLECT (one-directory: genera dist/APP MIO/) ─────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='APP MIO',          # nombre de la carpeta en dist/
)
