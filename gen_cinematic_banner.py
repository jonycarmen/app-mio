from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os, random

W, H = 1865, 108
random.seed(77)

img  = Image.new("RGB", (W, H), (5, 3, 12))
draw = ImageDraw.Draw(img)

# ── 1. NIGHT SKY GRADIENT ────────────────────────────────────────────────────
for y in range(H):
    t = y / H
    draw.line([(0, y), (W, y)], fill=(int(6+8*t), int(4+6*t), int(14+20*t)))

# ── 2. WET GROUND (bottom 38%) ───────────────────────────────────────────────
gy0 = int(H * 0.62)
for y in range(gy0, H):
    t = (y - gy0) / (H - gy0)
    draw.line([(0, y), (W, y)], fill=(int(10+12*t), int(6+8*t), int(22+18*t)))

# Ground puddle reflections
for _ in range(80):
    rx  = random.randint(0, W)
    ry  = random.randint(gy0 + 5, H - 3)
    rw  = random.randint(30, 160)
    alp = random.randint(8, 40)
    draw.line([(rx, ry), (rx+rw, ry)], fill=(alp//2, 0, alp*2), width=1)

# ── 3. GAS STATION CANOPY (right 45%) ────────────────────────────────────────
cx0 = int(W * 0.52)
cy0 = int(H * 0.05)
cw  = W - cx0
ch  = int(H * 0.20)
# Canopy body
draw.rectangle([cx0, cy0, W, cy0+ch], fill=(14, 10, 24))
draw.rectangle([cx0, cy0, W, cy0+3],  fill=(30, 22, 50))  # top edge
draw.rectangle([cx0, cy0+ch-2, W, cy0+ch], fill=(25, 18, 42))  # bottom edge

# Support pillars
for pillar_x in [cx0+55, cx0+250, cx0+500, W-50]:
    pw = 10
    draw.rectangle([pillar_x, cy0+ch, pillar_x+pw, H], fill=(18, 13, 30))
    draw.rectangle([pillar_x-2, cy0+ch-3, pillar_x+pw+2, cy0+ch+3], fill=(28,20,46))

# Gas pumps
for pump_x in [int(W*0.73), int(W*0.82), int(W*0.91)]:
    pump_y = int(H * 0.32)
    draw.rectangle([pump_x, pump_y, pump_x+16, H-8], fill=(13, 10, 22))
    draw.rectangle([pump_x-3, pump_y-5, pump_x+19, pump_y+5], fill=(22, 16, 38))
    # Screen
    draw.rectangle([pump_x+2, pump_y+8, pump_x+14, pump_y+22], fill=(30, 15, 60))
    draw.rectangle([pump_x+3, pump_y+9, pump_x+13, pump_y+21], fill=(50, 20, 100))
    # Hose
    draw.line([(pump_x+14, pump_y+28), (pump_x+22, pump_y+42)], fill=(20,15,30), width=2)

# Kwik Trip sign (glowing neon)
sx, sy, sw, sh = int(W*0.58), 4, 155, 18
for i in range(10, 0, -1):
    a = int(18 * (i/10))
    draw.rectangle([sx-i, sy-i, sx+sw+i, sy+sh+i], fill=(a//2, a//3, a*2))
draw.rectangle([sx, sy, sx+sw, sy+sh], fill=(16, 12, 35))
draw.rectangle([sx, sy, sx+sw, sy+2],  fill=(50, 35, 90))

font_sign = None
for fp in ["C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/ariblk.ttf"]:
    if os.path.exists(fp):
        try: font_sign = ImageFont.truetype(fp, 13); break
        except: pass
if not font_sign: font_sign = ImageFont.load_default()
draw.text((sx+10, sy+3), "Kwik  Trip", font=font_sign, fill=(140, 120, 210))

# ── 4. CEILING LIGHTS under canopy ───────────────────────────────────────────
for lx, col in [(int(W*0.63),(70,55,150)), (int(W*0.76),(55,90,170)), (int(W*0.89),(65,80,160))]:
    ly = cy0 + ch
    # Glow aura
    for r in range(20, 0, -2):
        a  = int(50 * (r/20)**2)
        rc = min(255, col[0]+a)
        gc = min(255, col[1]+a)
        bc = min(255, col[2]+a)
        draw.ellipse([lx-r, ly-r//3, lx+r, ly+r//2], fill=(rc, gc, bc))
    # Cone downward
    for i in range(22, 0, -1):
        a = int(28 * (i/22))
        draw.polygon([(lx-i*4, ly+i*3), (lx,ly), (lx+i*4, ly+i*3)],
                     fill=(a//2, a//3, a*2))

# ── 5. RAIN ───────────────────────────────────────────────────────────────────
for _ in range(2200):
    rx  = random.randint(0, W)
    ry  = random.randint(0, H)
    rl  = random.randint(4, 11)
    alp = random.randint(18, 65)
    draw.line([(rx, ry), (rx-1, ry+rl)], fill=(alp, alp, alp+25), width=1)

# ── 6. PERSON SILHOUETTE (left quarter, standing, watching right) ─────────────
ppx = int(W * 0.24)
ppy = H

# White sneakers visible
draw.ellipse([ppx-7,  ppy-9,  ppx+1,  ppy-2], fill=(165, 160, 185))
draw.ellipse([ppx+3,  ppy-9,  ppx+11, ppy-2], fill=(160, 155, 180))
# Legs (dark)
draw.polygon([ppx-7, ppy, ppx-5, ppy-42, ppx+1, ppy-42, ppx+4, ppy],  fill=(9, 7, 16))
draw.polygon([ppx+3, ppy, ppx+5, ppy-42, ppx+11,ppy-42, ppx+13,ppy], fill=(11, 8, 18))
# Torso / hoodie
draw.polygon([ppx-9, ppy-70, ppx+13, ppy-70,
              ppx+11,ppy-42, ppx-8,  ppy-42], fill=(11, 8, 19))
# Hood/head
draw.ellipse([ppx-9, ppy-90, ppx+13, ppy-68], fill=(13, 9, 21))
# Arms hanging
draw.line([(ppx-9, ppy-64),(ppx-14,ppy-44)], fill=(13,9,21), width=5)
draw.line([(ppx+11,ppy-64),(ppx+15,ppy-44)], fill=(13,9,21), width=5)

# ── 7. GOTHIC NEON "DALTON LIFE" TEXT (center) ───────────────────────────────
font_gothic = None
# Prefer Old English / gothic fonts, then heavy fallbacks
font_candidates = [
    ("C:/Windows/Fonts/OLDENGL.TTF", 54),
    ("C:/Windows/Fonts/Gabriola.ttf", 62),
    ("C:/Windows/Fonts/impact.ttf", 56),
    ("C:/Windows/Fonts/ariblk.ttf", 54),
]
for fp, sz in font_candidates:
    if os.path.exists(fp):
        try: font_gothic = ImageFont.truetype(fp, sz); break
        except: pass
if not font_gothic:
    font_gothic = ImageFont.load_default()

TEXT = "DALTON  LIFE"
bb   = draw.textbbox((0,0), TEXT, font=font_gothic)
tw   = bb[2]-bb[0];  th = bb[3]-bb[1]
tx   = (W - tw) // 2
ty   = (H - th) // 2 - 2

# --- Outer soft glow blob (blurred layer) ---
glow_layer = Image.new("RGB", (W, H), (0,0,0))
gd = ImageDraw.Draw(glow_layer)
for ox, oy in [(-6,0),(6,0),(0,-4),(0,4),(-4,-4),(4,-4),(-4,4),(4,4),
               (-9,0),(9,0),(0,-7),(0,7)]:
    gd.text((tx+ox, ty+oy), TEXT, font=font_gothic, fill=(100, 0, 180))
glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=5))
img = Image.blend(img, glow_blurred, 0.85)
draw = ImageDraw.Draw(img)

# --- Medium glow (closer) ---
for ox, oy in [(-2,0),(2,0),(0,-2),(0,2)]:
    draw.text((tx+ox, ty+oy), TEXT, font=font_gothic, fill=(170, 50, 240))

# --- Core text: purple → electric blue gradient ---
letters = list(TEXT)
cur_x   = tx
for i, ch in enumerate(letters):
    t_l = i / max(len(letters)-1, 1)
    r_c = int(180 - 80*t_l)
    g_c = int(20  + 20*t_l)
    b_c = int(220 + 35*t_l)
    draw.text((cur_x, ty), ch, font=font_gothic, fill=(r_c, g_c, b_c))
    lb = draw.textbbox((0,0), ch, font=font_gothic)
    cur_x += lb[2]-lb[0]

# Underline flare
draw.line([(tx, ty+th+2), (tx+tw, ty+th+2)], fill=(100, 0, 180), width=1)

# ── 8. ATMOSPHERIC HAZE ──────────────────────────────────────────────────────
haze = Image.new("RGB", (W, H), (0,0,0))
hd   = ImageDraw.Draw(haze)
for _ in range(14):
    hx  = random.randint(int(W*0.3), W)
    hy  = random.randint(int(H*0.25), int(H*0.75))
    hw  = random.randint(250, 600)
    hh2 = random.randint(12, 28)
    ha  = random.randint(6, 16)
    hd.ellipse([hx, hy, hx+hw, hy+hh2], fill=(ha, ha//2, ha+10))
img = Image.blend(img, haze, 0.25)
draw = ImageDraw.Draw(img)

# ── 9. VIGNETTE (dark purple edges, NO red) ──────────────────────────────────
for i in range(220):
    t2  = ((220-i)/220)**1.8
    val = int(160*t2)
    # Pure dark purple vignette
    for y in range(H):
        px_orig = img.getpixel((i, y))
        img.putpixel((i, y), (max(0,px_orig[0]-val), max(0,px_orig[1]-val), max(0,px_orig[2]-val//2)))
        px_orig2 = img.getpixel((W-1-i, y))
        img.putpixel((W-1-i, y), (max(0,px_orig2[0]-val), max(0,px_orig2[1]-val), max(0,px_orig2[2]-val//2)))

# Top and bottom darkening
for i in range(18):
    t3  = ((18-i)/18)**2
    val2= int(130*t3)
    for x in range(W):
        p = img.getpixel((x, i))
        img.putpixel((x, i), (max(0,p[0]-val2), max(0,p[1]-val2), max(0,p[2]-val2)))
        p2 = img.getpixel((x, H-1-i))
        img.putpixel((x, H-1-i), (max(0,p2[0]-val2), max(0,p2[1]-val2), max(0,p2[2]-val2)))

# ── 10. FILM GRAIN ───────────────────────────────────────────────────────────
for _ in range(W*H//7):
    gx3 = random.randint(0, W-1)
    gy3 = random.randint(0, H-1)
    v   = random.randint(185, 255)
    p   = img.getpixel((gx3, gy3))
    img.putpixel((gx3, gy3), tuple(min(255, c+v//30) for c in p))

# ── SAVE ─────────────────────────────────────────────────────────────────────
out = r"C:\Users\Jonathan Rosa\OneDrive\Desktop\APP MIO\banner_cinematic.png"
img.save(out, "PNG")
print(f"Saved {W}x{H} -> {out}")
