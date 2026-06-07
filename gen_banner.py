from PIL import Image, ImageDraw, ImageFont
import math, os, random

W, H = 1865, 108
img = Image.new("RGB", (W, H), (5, 3, 10))
draw = ImageDraw.Draw(img)

# Background gradient dark
for y in range(H):
    t = y / H
    r = int(6 + 4 * t)
    g = int(3 + 2 * t)
    b = int(10 + 8 * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Brick texture subtle
for row in range(0, H, 16):
    off = 30 if (row // 16) % 2 else 0
    for col in range(-30 + off, W, 70):
        draw.rectangle([col+1, row+1, col+65, row+13], outline=(22, 14, 28), width=1)

# Purple neon ground glow
for i in range(30, 0, -1):
    intensity = int(90 * (i / 30) ** 2)
    draw.line([(0, H - i), (W, H - i)], fill=(intensity // 2, 0, intensity))

# Speed lines left zone
random.seed(5)
for lx in range(130, 200, 12):
    a = random.randint(15, 40)
    draw.line([(lx, 0), (lx - 8, H)], fill=(a * 2, 0, a * 3), width=1)

# ── GIRL SILHOUETTE ──────────────────────────────────────────────────────────
gx, gy = 72, H

# Shoes
draw.ellipse([gx-12, gy-8, gx-1, gy], fill=(10, 8, 15))
draw.ellipse([gx+3, gy-8, gx+16, gy], fill=(10, 8, 15))

# Legs
draw.polygon([gx-11, gy, gx-7, gy-42, gx-1, gy-42, gx+4, gy], fill=(12, 8, 18))
draw.polygon([gx+2, gy, gx+4, gy-42, gx+12, gy-42, gx+16, gy], fill=(15, 10, 22))
for ry in [gy-16, gy-25, gy-34]:
    draw.line([(gx-9, ry), (gx-4, ry+2)], fill=(35, 25, 45), width=1)
    draw.line([(gx+6, ry), (gx+11, ry+2)], fill=(35, 25, 45), width=1)

# Torso
draw.polygon([gx-10, gy-68, gx+14, gy-68, gx+12, gy-44, gx-8, gy-44], fill=(18, 12, 24))
draw.rectangle([gx-7, gy-44, gx+11, gy-40], fill=(190, 140, 120))

# Checkered jacket
for cx0, cy0, cx1, cy1 in [(gx-18, gy-68, gx-10, gy-44), (gx+14, gy-68, gx+22, gy-44)]:
    bw = 5
    for ci in range(0, int(cx1-cx0), bw):
        for cj in range(0, int(cy1-cy0), bw):
            col2 = (170, 160, 170) if (ci//bw + cj//bw) % 2 == 0 else (20, 14, 26)
            draw.rectangle([int(cx0+ci), int(cy0+cj), int(cx0+ci+bw-1), int(cy0+cj+bw-1)], fill=col2)

# Neck + head
draw.rectangle([gx-3, gy-76, gx+5, gy-68], fill=(190, 140, 120))
draw.ellipse([gx-10, gy-90, gx+12, gy-68], fill=(190, 140, 120))

# Beanie
draw.rectangle([gx-11, gy-94, gx+13, gy-82], fill=(12, 10, 16))
draw.rectangle([gx-9, gy-96, gx+11, gy-92], fill=(18, 14, 22))

# Orange hair
draw.polygon([(gx-10, gy-88), (gx-20, gy-70), (gx-16, gy-52), (gx-9, gy-76)], fill=(200, 55, 15))
draw.polygon([(gx+12, gy-88), (gx+22, gy-65), (gx+18, gy-50), (gx+11, gy-76)], fill=(215, 65, 10))

# Arm + spray can
draw.line([(gx+12, gy-64), (gx+42, gy-56)], fill=(190, 140, 120), width=4)
draw.rectangle([gx+40, gy-63, gx+50, gy-48], fill=(90, 0, 120))
draw.ellipse([gx+41, gy-66, gx+49, gy-61], fill=(110, 0, 140))
draw.rectangle([gx+43, gy-68, gx+46, gy-64], fill=(60, 0, 90))

# Left arm relaxed
draw.line([(gx-10, gy-64), (gx-22, gy-50)], fill=(190, 140, 120), width=4)

# ── SPRAY CLOUD ─────────────────────────────────────────────────────────────
random.seed(7)
spray_cx, spray_cy = gx + 65, gy - 55
for _ in range(700):
    sx = spray_cx + random.gauss(0, 18)
    sy = spray_cy + random.gauss(0, 10)
    dist = math.sqrt((sx - spray_cx)**2 + (sy - spray_cy)**2)
    if 0 <= int(sx) < W and 0 <= int(sy) < H:
        intensity = max(0, int(200 - dist * 8))
        draw.point((int(sx), int(sy)), fill=(intensity // 2, 0, intensity))

# ── FONTS ────────────────────────────────────────────────────────────────────
font_main = font_sub = font_life = font_tag2 = font_r = None
for fp in ["C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/verdana.ttf"]:
    if os.path.exists(fp):
        try:
            font_main = ImageFont.truetype(fp, 58)
            font_sub  = ImageFont.truetype(fp, 28)
            font_life = ImageFont.truetype(fp, 32)
            font_tag2 = ImageFont.truetype(fp, 13)
            font_r    = ImageFont.truetype(fp, 20)
            break
        except:
            pass
if not font_main:
    font_main = font_sub = font_life = font_tag2 = font_r = ImageFont.load_default()

# ── CENTER LOGO: DALTON LIFE ────────────────────────────────────────────────
logo_x = W // 2 - 160
logo_y = H // 2 - 30

# Shadow
for ox, oy in [(5,5),(4,4),(3,3)]:
    draw.text((logo_x+ox, logo_y+oy), "DALTON", font=font_main, fill=(30, 0, 50))

# Glow
for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
    draw.text((logo_x+ox, logo_y+oy), "DALTON", font=font_main, fill=(180, 50, 240))

# Main
draw.text((logo_x, logo_y), "DALTON", font=font_main, fill=(148, 0, 211))

bbox = draw.textbbox((0, 0), "DALTON", font=font_main)
dalton_w = bbox[2] - bbox[0]

# LIFE box
lx = logo_x + dalton_w + 14
ly = logo_y + 10
lbbox = draw.textbbox((0, 0), "LIFE", font=font_life)
lw, lh = lbbox[2]-lbbox[0], lbbox[3]-lbbox[1]
draw.rectangle([lx-6, ly-4, lx+lw+6, ly+lh+4], fill=(230, 225, 80))
draw.rectangle([lx-4, ly-2, lx+lw+4, ly+lh+2], outline=(170, 165, 40), width=2)
draw.text((lx, ly), "LIFE", font=font_life, fill=(140, 0, 160))

# Tagline
draw.text((logo_x+4, logo_y+60), "* STREET  *  AUTHENTIC  *  RAW *", font=font_tag2, fill=(100, 0, 140))

# Right graffiti text
rx = W - 280
draw.text((rx+3, H//2-22+3), "KEEP IT REAL", font=font_r, fill=(40, 0, 60))
draw.text((rx, H//2-22), "KEEP IT REAL", font=font_r, fill=(100, 0, 160))
draw.text((rx+8, H//2+2), "EST. 2024", font=font_r, fill=(170, 150, 0))

# Right silhouette
rx2 = W - 40
draw.polygon([rx2-6, H, rx2-4, H-50, rx2+6, H-50, rx2+8, H], fill=(12, 8, 18))
draw.rectangle([rx2-8, H-72, rx2+10, H-50], fill=(16, 11, 22))
draw.ellipse([rx2-7, H-86, rx2+9, H-70], fill=(16, 11, 22))
draw.line([(rx2-8, H-65), (rx2-20, H-52)], fill=(16, 11, 22), width=4)
draw.line([(rx2+10, H-65), (rx2+18, H-58)], fill=(16, 11, 22), width=4)

# Neon lines
draw.line([(0, H-5), (W, H-5)], fill=(148, 0, 211), width=2)
draw.line([(0, H-3), (W, H-3)], fill=(80, 0, 120), width=1)
draw.line([(0, 3), (W, 3)], fill=(60, 0, 90), width=1)

# Vignette
for i in range(120):
    t2 = ((120-i)/120) ** 1.5
    v2 = int(140*t2)
    px = img.getpixel((i, H//2))
    img.putpixel((i, H//2), (max(0, px[0]-v2), max(0, px[1]-v2), max(0, px[2]-v2)))

# Film grain
random.seed(99)
for _ in range(W * H // 6):
    gx3 = random.randint(0, W-1)
    gy3 = random.randint(0, H-1)
    v = random.randint(200, 255)
    px = img.getpixel((gx3, gy3))
    img.putpixel((gx3, gy3), tuple(min(255, c + v//30) for c in px))

out = r"C:\Users\Jonathan Rosa\OneDrive\Desktop\APP MIO\banner_dalton_life.png"
img.save(out, "PNG")
print(f"Done: {W}x{H} -> {out}")
