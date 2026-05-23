"""
build_desktop.py — Script de build para generar el .exe de APP MIO.

Uso:
    py -3.12 build_desktop.py

Realiza:
  1. Verifica dependencias de build (pywebview, PyInstaller)
  2. Genera app_icon.ico si no existe (requiere Pillow)
  3. Limpia builds anteriores (build/ y dist/)
  4. Ejecuta PyInstaller con app_mio.spec
  5. Muestra la ruta del ejecutable generado
"""

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
DIST_DIR = ROOT / "dist" / "APP MIO"
EXE_PATH = DIST_DIR / "APP MIO.exe"
SPEC_FILE = ROOT / "app_mio.spec"
ICON_FILE = ROOT / "app_icon.ico"


def check() -> None:
    """Verifica que las dependencias de build estén instaladas."""
    missing = []
    for pkg, import_name in [
        ("pywebview", "webview"),
        ("pyinstaller", "PyInstaller"),
    ]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("[ERROR] Faltan dependencias de build:")
        for m in missing:
            print(f"  - {m}")
        print("\nInstálalas con:")
        print("  py -3.12 -m pip install -r requirements-desktop.txt")
        sys.exit(1)

    print("[OK] Dependencias de build verificadas")


def generate_icon() -> None:
    """Genera app_icon.ico usando Pillow (si no existe ya)."""
    if ICON_FILE.exists():
        print(f"[OK] Icono encontrado: {ICON_FILE.name}")
        return

    try:
        import importlib
        importlib.import_module("PIL")
    except ImportError:
        print("[WARN] Pillow no instalado — omitiendo generación de icono")
        print("       Instala Pillow para generarlo: py -3.12 -m pip install Pillow")
        print("       O copia manualmente app_icon.ico al directorio raíz del proyecto")
        return

    print("[INFO] Generando app_icon.ico…")
    result = subprocess.run(
        [sys.executable, str(ROOT / "create_icon.py")],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("[WARN] No se pudo generar el icono — continuando sin él")


def clean() -> None:
    """Elimina build/ y dist/ anteriores."""
    for dirname in ("build", "dist"):
        p = ROOT / dirname
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            print(f"[INFO] Limpiado: {dirname}/")


def build() -> None:
    """Ejecuta PyInstaller."""
    if not SPEC_FILE.exists():
        print(f"[ERROR] No se encontró {SPEC_FILE}")
        sys.exit(1)

    print("[INFO] Ejecutando PyInstaller…")
    print(f"       Spec: {SPEC_FILE}")
    print()

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", str(SPEC_FILE)],
        cwd=str(ROOT),
    )

    if result.returncode != 0:
        print("\n[ERROR] PyInstaller falló. Revisa los mensajes anteriores.")
        sys.exit(1)


def post_build() -> None:
    """Copia archivos extra necesarios al directorio de distribución."""
    env_example = ROOT / ".env.example"
    dest_env = DIST_DIR / ".env.example"

    # .env.example ya se incluye vía spec datas, pero por si acaso:
    if env_example.exists() and not dest_env.exists():
        shutil.copy(env_example, dest_env)
        print(f"[INFO] Copiado: .env.example → dist/APP MIO/")

    # Crear README de uso para el usuario final
    user_readme = DIST_DIR / "LEEME.txt"
    if not user_readme.exists():
        user_readme.write_text(
            "APP MIO — Instrucciones de uso\n"
            "==============================\n\n"
            "1. Copia '.env.example' como '.env' y edita los valores.\n"
            "2. Ejecuta 'APP MIO.exe'.\n"
            "   La base de datos y el almacenamiento se crean automáticamente.\n\n"
            "Archivos importantes:\n"
            "  .env          — Configuración (credenciales, SMTP, etc.)\n"
            "  app.db        — Base de datos SQLite (se crea al primer arranque)\n"
            "  storage/      — Archivos subidos (PDFs, fotos, branding)\n"
            "  logs/         — Registros de la aplicación\n\n"
            "NOTA: No borres ni muevas estos archivos o la app perderá datos.\n",
            encoding="utf-8",
        )
        print("[INFO] Creado: dist/APP MIO/LEEME.txt")


def main() -> None:
    print("=" * 60)
    print("  Build de APP MIO Desktop")
    print("=" * 60)
    print()

    check()
    generate_icon()
    clean()
    build()
    post_build()

    print()
    print("=" * 60)
    print("[OK] Build completado exitosamente")
    print(f"     Ejecutable: {EXE_PATH}")
    print()
    print("Para distribuir:")
    print("  Comprime toda la carpeta 'dist/APP MIO/' y entrégala al usuario.")
    print("  El usuario debe crear/editar '.env' antes de ejecutar la app.")
    print("=" * 60)


if __name__ == "__main__":
    main()
