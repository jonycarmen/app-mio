"""
create_icon.py — Genera app_icon.ico para APP MIO.

Requiere Pillow:
    py -3.12 -m pip install Pillow

Uso:
    py -3.12 create_icon.py
"""

from pathlib import Path


def create_icon() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[ERROR] Pillow no está instalado.")
        print("        Instálalo con: py -3.12 -m pip install Pillow")
        return

    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames: list = []

    # Paleta de colores: fondo índigo, texto blanco
    BG_COLOR    = (99, 102, 241, 255)   # indigo-500
    DARK_COLOR  = (67, 56, 202, 255)    # indigo-700 (para sombra/borde)
    TEXT_COLOR  = (255, 255, 255, 255)  # blanco
    SHINE_COLOR = (165, 180, 252, 80)   # indigo-300 semitransparente (brillo)

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Radio de esquinas: ~18 % del tamaño
        radius = max(int(size * 0.18), 3)

        # Fondo con esquinas redondeadas
        draw.rounded_rectangle(
            [(0, 0), (size - 1, size - 1)],
            radius=radius,
            fill=BG_COLOR,
        )

        # Borde inferior ligeramente más oscuro (profundidad)
        border_w = max(1, size // 32)
        draw.rounded_rectangle(
            [(border_w, border_w), (size - 1 - border_w, size - 1 - border_w)],
            radius=max(radius - 1, 2),
            outline=DARK_COLOR,
            width=border_w,
        )

        # Brillo en la esquina superior izquierda
        if size >= 32:
            shine_r = size // 3
            draw.ellipse(
                [(-shine_r // 2, -shine_r // 2), (shine_r, shine_r)],
                fill=SHINE_COLOR,
            )

        # Texto "AM"
        text = "AM"
        font_size = max(int(size * 0.42), 6)
        font = None
        for font_name in ("arialbd.ttf", "arial.ttf", "calibrib.ttf", "calibri.ttf"):
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (size - tw) // 2 - bbox[0]
        ty = (size - th) // 2 - bbox[1]
        draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)

        frames.append(img)

    out = Path(__file__).parent / "app_icon.ico"
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"[OK] Icono generado: {out}")


if __name__ == "__main__":
    create_icon()
