from PIL import Image, ImageDraw, ImageFont
import math, os, random

W, H = 1865, 108
FRAMES = 40

# ── FONTS ────────────────────────────────────────────────────────────────────
font_main = font_life = font_tag = font_small = None
for fp in ["C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/verdana.ttf"]:
    if os.path.exists(fp):
        try:
            font_main  = ImageFont.truetype(fp, 58)
            font_life  = ImageFont.truetype(fp, 32)
            font_tag   = ImageFont.truetype(fp, 13)
            font_small = ImageFont.truetype(fp, 20)
            break
        except:
            pass
if not font_main:
    font_main = font_life = font_tag = font_small = ImageFont.load_default()

# Pre-measure text sizes
_tmp = Image.new("RGB", (10, 10))
_d   = ImageDraw.Draw(_tmp)
bb        = _d.textbbox((0, 0), "DALTON", font=font_main)
DALTON_W  = bb[2] - bb[0]
DALTON_H  = bb[3] - bb[1]
bb2       = _d.textbbox((0, 0), "LIFE", font=font_life)
LIFE_W    = bb2[2] - bb2[0]
LIFE_H    = bb2[3] - bb2[1]

# Graffiti centered in banner
GRAFFITI_X = W // 2 - (DALTON_W + 14 + LIFE_W + 12) // 2
GRAFFITI_Y = H // 2 - 30
LIFE_X     = GRAFFITI_X + DALTON_W + 14
LIFE_Y     = GRAFFITI_Y + 10

# Character travel path: enters from RIGHT, stops just right of graffiti
GX_START = W + 35          # off-screen right
GX_FINAL = LIFE_X + LIFE_W + 60   # stops right of the finished graffiti

def draw_background(draw):
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=(int(6+4*t), int(3+2*t), int(10+8*t)))
    for row in range(0, H, 16):
        off = 30 if (row // 16) % 2 else 0
        for col in range(-30 + off, W, 70):
            draw.rectangle([col+1, row+1, col+65, row+13], outline=(22, 14, 28), width=1)
    for i in range(30, 0, -1):
        intensity = int(90 * (i/30)**2)
        draw.line([(0, H-i), (W, H-i)], fill=(intensity//2, 0, intensity))
    draw.line([(0, 3),    (W, 3)],    fill=(60, 0, 90),   width=1)
    draw.line([(0, H-5),  (W, H-5)],  fill=(148, 0, 211), width=2)
    draw.line([(0, H-3),  (W, H-3)],  fill=(80, 0, 120),  width=1)

def draw_girl_flipped(draw, gx, gy, arm_sweep_deg=0, frame=0):
    """
    Girl facing LEFT (mirrored). Spray arm extends to the LEFT.
    arm_sweep_deg: horizontal sweep of left arm from -30 (far left) to +10 (close).
    Returns nozzle (tip of spray can) position.
    """
    bob = int(3 * math.sin(frame * 0.8))

    # Shoes (left-facing)
    draw.ellipse([gx-16, gy-8,  gx-5,  gy+bob], fill=(10, 8, 15))
    draw.ellipse([gx+1,  gy-8,  gx+12, gy+bob], fill=(10, 8, 15))

    # Legs
    draw.polygon([gx-16, gy, gx-12, gy-42, gx-6,  gy-42, gx-1, gy], fill=(12, 8, 18))
    draw.polygon([gx-2,  gy, gx,    gy-42, gx+10, gy-42, gx+14,gy], fill=(15, 10, 22))
    for ry in [gy-16, gy-25, gy-34]:
        draw.line([(gx-13, ry), (gx-8,  ry+2)], fill=(35, 25, 45), width=1)
        draw.line([(gx+3,  ry), (gx+9,  ry+2)], fill=(35, 25, 45), width=1)

    # Torso
    draw.polygon([gx-14, gy-68, gx+10, gy-68, gx+8, gy-44, gx-12, gy-44], fill=(18, 12, 24))
    draw.rectangle([gx-9,  gy-44, gx+7,  gy-40], fill=(190, 140, 120))  # midriff

    # Checkered jacket panels (mirrored sides)
    for cx0, cy0, cx1, cy1 in [(gx+10, gy-68, gx+18, gy-44), (gx-22, gy-68, gx-14, gy-44)]:
        bw = 5
        for ci in range(0, int(cx1-cx0), bw):
            for cj in range(0, int(cy1-cy0), bw):
                col2 = (170,160,170) if (ci//bw+cj//bw)%2==0 else (20,14,26)
                draw.rectangle([int(cx0+ci), int(cy0+cj), int(cx0+ci+bw-1), int(cy0+cj+bw-1)], fill=col2)

    # Neck + head
    draw.rectangle([gx-5, gy-76, gx+3, gy-68], fill=(190, 140, 120))
    draw.ellipse([gx-12, gy-90, gx+10, gy-68],  fill=(190, 140, 120))

    # Beanie
    draw.rectangle([gx-13, gy-94, gx+11, gy-82], fill=(12, 10, 16))
    draw.rectangle([gx-11, gy-96, gx+9,  gy-92], fill=(18, 14, 22))

    # Hair (flipped — falls to the right side for left-facing char)
    draw.polygon([(gx+10, gy-88),(gx+20, gy-70),(gx+16, gy-52),(gx+9,  gy-76)], fill=(200, 55, 15))
    draw.polygon([(gx-12, gy-88),(gx-22, gy-65),(gx-18, gy-50),(gx-11, gy-76)], fill=(215, 65, 10))

    # LEFT arm extended with spray can (arm reaches LEFT toward graffiti)
    arm_dx = int(-30 - 8 * math.cos(math.radians(arm_sweep_deg)))
    arm_dy = int(-8  + 4 * math.sin(math.radians(arm_sweep_deg)))
    ax_end = gx - 12 + arm_dx
    ay_end = gy - 64 + arm_dy
    # clamp to canvas
    ax_end = max(0, min(W-1, ax_end))
    ay_end = max(0, min(H-1, ay_end))
    draw.line([(gx-12, gy-64), (ax_end, ay_end)], fill=(190, 140, 120), width=4)
    # Spray can
    draw.rectangle([ax_end-8, ay_end-7, ax_end+2,  ay_end+7],  fill=(90, 0, 120))
    draw.ellipse([ax_end-7,  ay_end-10, ax_end+1,  ay_end-5],  fill=(110, 0, 140))
    draw.rectangle([ax_end-5, ay_end-13, ax_end-2, ay_end-8],  fill=(60, 0, 90))  # nozzle tip

    # Right arm (relaxed bob)
    la_dy = int(3 * math.sin(math.radians(frame * 20)))
    draw.line([(gx+8, gy-64), (gx+20, gy-50+la_dy)], fill=(190, 140, 120), width=4)

    return ax_end, ay_end  # nozzle tip

def draw_spray_particles(draw, nozzle_x, nozzle_y, reveal_frac, rng):
    """Particles fly LEFT from nozzle toward current paint edge."""
    # Current paint edge x (right-to-left reveal means edge goes from right to left)
    paint_edge_x = GRAFFITI_X + DALTON_W - int(DALTON_W * min(1.0, reveal_frac * 1.6))
    target_x = max(GRAFFITI_X, paint_edge_x)
    target_y = GRAFFITI_Y + DALTON_H // 2

    dx = target_x - nozzle_x
    dy = target_y - nozzle_y
    length = math.sqrt(dx*dx + dy*dy) or 1
    nx, ny = dx/length, dy/length

    for _ in range(90):
        dist   = rng.uniform(5, length * 0.9)
        spread = rng.gauss(0, 9)
        px = int(nozzle_x + nx*dist - ny*spread)
        py = int(nozzle_y + ny*dist + nx*spread)
        if 0 <= px < W and 0 <= py < H:
            alpha = max(60, int(200 - dist * 1.1))
            size  = rng.randint(1, 3)
            draw.ellipse([px-size, py-size, px+size, py+size], fill=(alpha//2, 0, alpha))

def draw_graffiti(img, draw, reveal_frac):
    """DALTON reveals RIGHT → LEFT; LIFE box after."""
    if reveal_frac <= 0:
        return

    gx0, gy0 = GRAFFITI_X, GRAFFITI_Y

    # --- DALTON (right-to-left reveal) ---
    dalton_frac  = min(1.0, reveal_frac * 1.6)
    revealed_px  = int(DALTON_W * dalton_frac)   # how many px from RIGHT are revealed
    start_col    = DALTON_W - revealed_px          # leftmost revealed column

    if revealed_px > 0:
        tmp = Image.new("RGBA", (DALTON_W + 10, DALTON_H + 10), (0, 0, 0, 0))
        td  = ImageDraw.Draw(tmp)
        for ox, oy in [(4,4),(3,3),(2,2)]:
            td.text((ox, oy), "DALTON", font=font_main, fill=(30, 0, 50, 255))
        for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
            td.text((ox, oy), "DALTON", font=font_main, fill=(180, 50, 240, 200))
        td.text((0, 0), "DALTON", font=font_main, fill=(148, 0, 211, 255))

        # Crop: keep only [start_col .. DALTON_W]
        cropped = tmp.crop((start_col, 0, DALTON_W+10, DALTON_H+10))
        img.paste(cropped, (gx0 + start_col, gy0), cropped)

        # Wet drip on the paint front edge
        if dalton_frac < 1.0 and start_col > 0:
            edge_x = gx0 + start_col
            for dy2 in range(0, DALTON_H, 7):
                if random.random() < 0.45:
                    drip_len = random.randint(3, 12)
                    draw.line([(edge_x, gy0+dy2), (edge_x, gy0+dy2+drip_len)],
                              fill=(148, 0, 211), width=2)

    # --- LIFE box (appears after DALTON is ~62% done) ---
    life_frac = max(0.0, (reveal_frac - 0.62) / 0.38)
    if life_frac > 0:
        lx, ly  = LIFE_X, LIFE_Y
        # Box also reveals right-to-left
        box_total = LIFE_W + 12
        box_shown = int(box_total * life_frac)
        box_left  = lx - 6 + (box_total - box_shown)
        if box_shown > 0:
            draw.rectangle([box_left, ly-4, lx+LIFE_W+6, ly+LIFE_H+4], fill=(230, 225, 80))
            if lx+LIFE_W+4 > box_left+2:
                draw.rectangle([box_left+2, ly-2, lx+LIFE_W+4, ly+LIFE_H+2],
                               outline=(170, 165, 40), width=2)
        life_text_start = int(LIFE_W * (1.0 - life_frac))
        life_text_px    = LIFE_W - life_text_start
        if life_text_px > 0:
            tmp2 = Image.new("RGBA", (LIFE_W+10, LIFE_H+10), (0, 0, 0, 0))
            td2  = ImageDraw.Draw(tmp2)
            td2.text((0, 0), "LIFE", font=font_life, fill=(140, 0, 160, 255))
            cropped2 = tmp2.crop((life_text_start, 0, LIFE_W+10, LIFE_H+10))
            img.paste(cropped2, (lx + life_text_start, ly), cropped2)

def draw_right_figure(draw):
    rx2 = W - 40
    draw.polygon([rx2-6,H, rx2-4,H-50, rx2+6,H-50, rx2+8,H], fill=(12, 8, 18))
    draw.rectangle([rx2-8,H-72, rx2+10,H-50],  fill=(16, 11, 22))
    draw.ellipse([rx2-7,H-86,   rx2+9, H-70],   fill=(16, 11, 22))
    draw.line([(rx2-8,H-65),(rx2-20,H-52)], fill=(16,11,22), width=4)
    draw.line([(rx2+10,H-65),(rx2+18,H-58)], fill=(16,11,22), width=4)

# ── BUILD FRAMES ─────────────────────────────────────────────────────────────
frames = []
rng = random.Random(123)

for f in range(FRAMES):
    img  = Image.new("RGB", (W, H), (5, 3, 10))
    draw = ImageDraw.Draw(img)
    draw_background(draw)

    # Ease-in-out for character slide
    raw_t = min(1.0, f / 8)
    ease  = raw_t * raw_t * (3 - 2 * raw_t)
    gx    = int(GX_START + (GX_FINAL - GX_START) * ease)
    gy    = H

    # Graffiti starts revealing from frame 6 onward
    graffiti_frac = max(0.0, (f - 6) / (FRAMES - 10))

    # Arm sweep: goes from right (0°) sweeping LEFT as graffiti reveals
    arm_sweep = 0 + graffiti_frac * -40   # 0 → -40 deg (sweeps left)
    arm_bob   = 8 * math.sin(f * 0.9)

    nozzle_x, nozzle_y = draw_girl_flipped(draw, gx, gy,
                                            arm_sweep_deg=arm_sweep + arm_bob,
                                            frame=f)

    # Spray particles while painting
    if 6 <= f <= FRAMES - 4 and graffiti_frac < 1.0:
        draw_spray_particles(draw, nozzle_x, nozzle_y, graffiti_frac, rng)

    # Graffiti reveal
    if f >= 6:
        draw_graffiti(img, draw, graffiti_frac)

    # Logo glow pulse on last frames
    if f >= FRAMES - 5:
        pulse = 0.5 + 0.5 * math.sin((f - (FRAMES-5)) * math.pi / 2)
        glow  = Image.new("RGB", (W, H), (0, 0, 0))
        gd    = ImageDraw.Draw(glow)
        gc    = int(30 * pulse)
        gd.rectangle([GRAFFITI_X-20, GRAFFITI_Y-5,
                       LIFE_X+LIFE_W+20, GRAFFITI_Y+DALTON_H+10],
                     fill=(gc, 0, gc*2))
        img   = Image.blend(img, glow, 0.3)
        draw  = ImageDraw.Draw(img)

    draw_right_figure(draw)

    # Film grain
    rng2 = random.Random(f * 17)
    for _ in range(W * H // 20):
        gx3 = rng2.randint(0, W-1)
        gy3 = rng2.randint(0, H-1)
        v   = rng2.randint(200, 255)
        px  = img.getpixel((gx3, gy3))
        img.putpixel((gx3, gy3), tuple(min(255, c + v//35) for c in px))

    frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    print(f"Frame {f+1}/{FRAMES}", end="\r")

print()

out = r"C:\Users\Jonathan Rosa\OneDrive\Desktop\APP MIO\banner_dalton_anim.gif"
frames[0].save(
    out,
    save_all=True,
    append_images=frames[1:],
    loop=0,
    duration=65,
    optimize=True,
)
print(f"GIF saved: {out}  ({FRAMES} frames, 1865x108)")
