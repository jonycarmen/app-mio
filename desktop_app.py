"""desktop_app.py — Launcher de escritorio para APP MIO.

Arranca el servidor FastAPI (uvicorn) en un hilo secundario y abre una
ventana nativa del navegador (pywebview / Edge WebView2).

Uso en desarrollo:
    py -3.12 desktop_app.py

Uso como exe (generado por PyInstaller):
    APP MIO.exe
"""

import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Optional


# ── 1. Resolución de rutas base ───────────────────────────────────────────────

def _get_base_dir() -> Path:
    """
    Devuelve el directorio base:
    - bundle PyInstaller (one-dir): directorio que contiene el .exe
    - modo desarrollo: directorio que contiene este script
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()


BASE_DIR: Path = _get_base_dir()

# Cambiar CWD antes de cualquier import de la app para que las rutas
# relativas (templates, static, storage, app.db, .env) se resuelvan aquí.
os.chdir(BASE_DIR)

# Asegurar que el paquete 'app' sea importable
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ── 2. Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "logs" / "desktop.log", encoding="utf-8", errors="replace"),
    ],
)
log = logging.getLogger("desktop_app")

# ── 3. Configuración de red ───────────────────────────────────────────────────

_HOST = "127.0.0.1"
_PORT_BASE = 8765   # Puerto inicial; se busca uno libre automáticamente


# ── 4. Utilidades de red ──────────────────────────────────────────────────────

def _find_free_port(start: int = _PORT_BASE) -> int:
    """Devuelve el primer puerto TCP libre a partir de start."""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((_HOST, port)) != 0:
                return port
    return start


def _wait_for_server(host: str, port: int, timeout: float = 30.0) -> bool:
    """Espera hasta que el servidor acepte conexiones TCP o se agote el tiempo."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


# ── 5. Migraciones Alembic ────────────────────────────────────────────────────

def _run_migrations() -> None:
    """Aplica migraciones Alembic al arrancar (crea/actualiza app.db)."""
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig

        ini_path = BASE_DIR / "alembic.ini"
        if not ini_path.exists():
            log.warning("alembic.ini no encontrado en %s — omitiendo migraciones", BASE_DIR)
            return

        cfg = AlembicConfig(str(ini_path))
        # Sobrescribir script_location con ruta absoluta para compatibilidad con bundle
        cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
        command.upgrade(cfg, "head")
        log.info("Migraciones aplicadas correctamente")
    except Exception as exc:
        log.error("Error al aplicar migraciones: %s", exc, exc_info=True)


# ── 6. Título de la app desde la BD ──────────────────────────────────────────

def _get_app_title() -> str:
    """Lee app_name desde la tabla app_settings. Devuelve 'APP MIO' si falla."""
    try:
        from app.db import SessionLocal
        from app.models.app_settings import AppSettings

        db = SessionLocal()
        try:
            s = db.get(AppSettings, 1)
            if s and s.app_name:
                return s.app_name
        finally:
            db.close()
    except Exception:
        pass
    return "APP MIO"


# ── 7. Servidor uvicorn ───────────────────────────────────────────────────────

_uvicorn_server: Optional[object] = None  # uvicorn.Server


def _start_server(port: int) -> None:
    """Arranca uvicorn en el hilo que lo invoque (bloqueante)."""
    import uvicorn
    from app.main import app as fastapi_app

    global _uvicorn_server
    config = uvicorn.Config(
        fastapi_app,
        host=_HOST,
        port=port,
        log_level="warning",
        loop="asyncio",
        access_log=False,
    )
    _uvicorn_server = uvicorn.Server(config)
    _uvicorn_server.run()


def _stop_server() -> None:
    """Señaliza al servidor que debe detenerse (no bloqueante)."""
    if _uvicorn_server is not None:
        _uvicorn_server.should_exit = True


# ── 8. Splash HTML ────────────────────────────────────────────────────────────

_SPLASH_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Iniciando…</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      height: 100vh;
      background: #1e1e2e;
      font-family: system-ui, -apple-system, sans-serif;
      color: #cdd6f4;
    }
    .spinner {
      width: 52px; height: 52px;
      border: 5px solid #313244;
      border-top-color: #6366f1;
      border-radius: 50%;
      animation: spin .85s linear infinite;
      margin-bottom: 28px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    h2 { font-size: 1.5rem; font-weight: 600; margin-bottom: 10px; }
    p  { font-size: .95rem; color: #a6adc8; }
  </style>
</head>
<body>
  <div class="spinner"></div>
  <h2>Iniciando APP MIO…</h2>
  <p>Por favor espera un momento</p>
</body>
</html>
"""

_ERROR_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Error</title>
  <style>
    body {{
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      height: 100vh;
      background: #1e1e2e;
      font-family: system-ui, sans-serif;
      color: #f38ba8;
    }}
    h2 {{ font-size: 1.4rem; margin-bottom: 12px; }}
    p  {{ color: #cdd6f4; font-size: .9rem; max-width: 480px; text-align: center; }}
    code {{ background: #313244; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h2>Error al iniciar el servidor</h2>
  <p>{message}</p>
  <p style="margin-top:16px">Revisa el archivo <code>logs/desktop.log</code> para más detalles.</p>
</body>
</html>
"""


# ── 9. Punto de entrada ───────────────────────────────────────────────────────

def main() -> None:
    # Asegurar directorios necesarios antes de importar la app
    for sub in ("storage/pdfs", "storage/profiles", "storage/branding", "logs"):
        (BASE_DIR / sub).mkdir(parents=True, exist_ok=True)

    # Aplicar migraciones
    _run_migrations()

    # Buscar puerto libre
    port = _find_free_port(_PORT_BASE)
    url = f"http://{_HOST}:{port}"
    log.info("Iniciando servidor en %s", url)

    # Obtener título antes de abrir la ventana
    title = _get_app_title()

    import webview

    # Crear ventana con página splash mientras arranca el servidor
    window = webview.create_window(
        title=title,
        html=_SPLASH_HTML,
        width=1200,
        height=800,
        resizable=True,
        min_size=(800, 600),
    )

    def _on_closed() -> None:
        log.info("Ventana cerrada — deteniendo servidor")
        _stop_server()

    window.events.closed += _on_closed

    def _after_gui_start() -> None:
        """
        Llamada por pywebview en un hilo separado después de que la GUI esté lista.
        Arranca uvicorn y redirige la ventana cuando el servidor responde.
        """
        srv_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
        srv_thread.start()

        log.info("Esperando respuesta del servidor…")
        ready = _wait_for_server(_HOST, port, timeout=30.0)

        if ready:
            log.info("Servidor listo — cargando %s", url)
            window.load_url(url)
        else:
            log.error("El servidor no respondió en 30 segundos")
            msg = (
                "El servidor no arrancó en el tiempo esperado. "
                "Verifica que el archivo <code>.env</code> existe y es correcto, "
                "y que no hay otro proceso usando el puerto."
            )
            window.load_html(_ERROR_HTML.format(message=msg))

    # Detectar icono
    icon_path = BASE_DIR / "app_icon.ico"
    icon_arg = str(icon_path) if icon_path.exists() else None

    # Iniciar GUI (bloqueante hasta que se cierra la ventana)
    webview.start(
        func=_after_gui_start,
        gui="edgechromium",   # Windows: usa Edge WebView2 (pre-instalado en Win10/11)
        icon=icon_arg,
    )

    # Limpieza final tras cerrar la ventana
    _stop_server()
    log.info("APP MIO cerrada")


if __name__ == "__main__":
    main()
