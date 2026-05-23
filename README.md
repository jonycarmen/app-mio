# People PDF Payroll Manager

Aplicacion web en FastAPI para gestionar personas, documentos PDF y nominas con SQLite, SQLAlchemy y Jinja2.

## Requisitos

- Python 3.11+

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Migraciones de base de datos

El esquema de la base de datos se gestiona con Alembic. La base no se crea automaticamente al iniciar la app: hay que aplicar las migraciones primero.

```bash
alembic upgrade head
alembic current
alembic history
alembic revision --autogenerate -m "descripcion del cambio"
alembic downgrade -1
```

La configuracion de Alembic esta en `alembic.ini` y `migrations/env.py`. La URL de base de datos se toma de `app/config.py`.

## Arranque del servidor

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Para que los enlaces publicos funcionen desde otros dispositivos de la misma red local, arranca el servidor asi:

```bash
uvicorn app.main:app --host 0.0.0.0 --reload
```

Luego comparte un enlace con la IP local del servidor, por ejemplo `http://192.168.1.50:8000/form/<token>`.

## Funcionalidades

- CRUD de personas
- Enlaces publicos self-service por persona con token unico
- Multiples cuentas bancarias y wallets por persona
- Subida y visualizacion de PDFs
- Registro historico de nominas
- Interfaz web con Jinja2
- Busqueda avanzada por nombre, DNI, pasaporte, IBAN y direccion de wallet
- **Recuperacion de contrasena por email y/o SMS** (bcrypt + itsdangerous)

## Recuperacion de contrasena

El flujo es: `/admin/forgot-password` → `/admin/verify-code` → `/admin/reset-password`.

1. El administrador introduce su email o telefono registrado.
2. Recibe un codigo OTP de 6 digitos (expira en 15 min, hasheado con bcrypt en BD).
3. Introduce el codigo en la pantalla de verificacion (maximo 5 intentos).
4. Establece la nueva contrasena (minimo 8 caracteres).

**Rate limits**: 3 envios de codigo por hora (por IP), 5 intentos de verificacion por sesion.

### Configurar email SMTP

Edita `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu@gmail.com
```

### Configurar SMS Twilio (opcional)

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+14155238886
```

Si los valores de Twilio estan vacios, la opcion SMS no aparece en la interfaz.

### Tabla admins y admin por defecto

La migracion `0004` crea las tablas `admins` y `verification_codes`.
Al arrancar la app, si no hay ningun admin en BD, se crea automaticamente uno con las credenciales de `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).
Para añadir email/telefono al admin ejecuta una consulta directa o crea una ruta de perfil.

## Aplicacion de escritorio (Windows .exe)

La app puede empaquetarse como un ejecutable Windows standalone usando
PyWebView + PyInstaller. El .exe lanza el servidor FastAPI internamente y
abre una ventana nativa de Edge WebView2.

### Requisitos previos de build

- Windows 10 / 11 con Microsoft Edge instalado (Edge WebView2 Runtime)
- Python 3.12 instalado (`py -3.12`)
- Dependencias del servidor ya instaladas (`requirements.txt`)

### 1. Instalar dependencias de build

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 -m pip install -r requirements-desktop.txt
```

### 2. Generar el icono (opcional, requiere Pillow)

```bash
py -3.12 create_icon.py
```

Genera `app_icon.ico`. Puedes reemplazarlo por tu propio `.ico` antes del build.

### 3. Generar el .exe

```bash
py -3.12 build_desktop.py
```

Esto limpia builds anteriores y ejecuta PyInstaller con `app_mio.spec`.
El resultado queda en `dist/APP MIO/`.

Alternativa directa con PyInstaller:

```bash
py -3.12 -m PyInstaller --clean app_mio.spec
```

### 4. Probar antes de distribuir

```bash
cd "dist\APP MIO"
copy ..\..\\.env.example .env
# Edita .env con tus valores reales
"APP MIO.exe"
```

### 5. Distribuir

Comprime la carpeta `dist/APP MIO/` completa (ZIP o instalador).  
El usuario final necesita:

1. Descomprimir en cualquier carpeta (sin espacios recomendado).
2. Copiar `.env.example` como `.env` y editar credenciales.
3. Ejecutar `APP MIO.exe`.

La base de datos (`app.db`) y el almacenamiento (`storage/`) se crean
automáticamente en la misma carpeta al primer arranque.

### Archivos de la version de escritorio

| Archivo                  | Descripcion                                      |
|--------------------------|--------------------------------------------------|
| `desktop_app.py`         | Launcher principal (uvicorn + pywebview)         |
| `app_mio.spec`           | Configuracion PyInstaller (one-directory mode)   |
| `build_desktop.py`       | Script de build automatizado                     |
| `create_icon.py`         | Generador de icono .ico con Pillow               |
| `requirements-desktop.txt` | Dependencias adicionales de build              |

### Notas tecnicas

- **Modo one-directory**: el .exe genera una carpeta `dist/APP MIO/` con
  todos los archivos separados (mejor rendimiento que one-file).
- **Puerto**: el launcher busca automáticamente un puerto libre a partir
  del 8765; múltiples instancias pueden coexistir.
- **Migraciones**: se ejecutan automáticamente al arrancar con Alembic.
- **Edge WebView2**: preinstalado en Windows 10 (20H2+) y Windows 11.
  Para versiones anteriores, descarga el runtime desde
  https://developer.microsoft.com/microsoft-edge/webview2/

## Estructura

- `app/` - backend, plantillas y estaticos
- `migrations/` - scripts de migracion Alembic
- `storage/pdfs/` - archivos PDF locales
- `tests/` - pruebas API basicas
- `desktop_app.py` - launcher de escritorio
- `app_mio.spec` - configuracion PyInstaller