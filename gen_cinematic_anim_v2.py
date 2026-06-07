from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os, random

W, H   = 1865, 108
FRAMES = 45

# ── FONTS ────────────────────────────────────────────────────────────────────
font_gothic = font_sign = None
for fp, sz in [("C:/Windows/Fonts/OLDENGL.TTF",54),("C:/Windows/Fonts/Gabriola.ttf",62),
               ("C:/Windows/Fonts/impact.ttf",56),("C:/Windows/Fonts/ariblk.ttf",54)]:
    if os.path.exists(fp):
        try: font_gothic = ImageFont.truetype(fp, sz); break
        except: pass
for fp in ["C:/Windows/Fonts/impact.ttf","C:/Windows/Fonts/ariblk.ttf"]:
    if os.path.exists(fp):
        try: font_sign = ImageFont.truetype(fp, 13); break
        except: pass
if not font_gothic: font_gothic = ImageFont.load_default()
if not font_sign:   font_sign   = ImageFont.load_default()

_d  = ImageDraw.Draw(Image.new("RGB",(10,10)))
bb  = _d.textbbox((0,0),"DALTON  LIFE", font=font_gothic)
TW, TH = bb[2]-bb[0], bb[3]-bb[1]
TX  = (W - TW) // 2
TY  = (H - TH) // 2 - 2

RAIN_SETS = []
for s in range(FRAMES):
    rng = random.Random(s*31+5)
    RAIN_SETS.append([(rng.randint(0,W),rng.randint(0,H),
                       rng.randint(4,12),rng.randint(18,70)) for _ in range(2000)])

PUDDLE_SETS = []
for s in range(FRAMES):
    rng = random.Random(s*13+99)
    PUDDLE_SETS.append([(rng.randint(0,W),rng.randint(int(H*0.65),H-3),
                         rng.randint(30,180),rng.randint(6,38)) for _ in range(70)])

# ── SPRAY CAN DRAWING ─────────────────────────────────────────────────────────
def make_spray_can(target_h=96, angle_deg=-40):
    """
    Draw a cartoon spray can (purple/yellow) on transparent RGBA canvas,
    rotated to angle_deg, scaled to target_h tall.
    """
    # Draw upright first on a temp canvas
    CW, CH = 60, 110
    can = Image.new("RGBA", (CW, CH), (0,0,0,0))
    cd  = ImageDraw.Draw(can)

    # --- Body ---
    bx0,by0,bx1,by1 = 8, 28, 52, 90
    # Shadow/depth left
    cd.ellipse([bx0, by0+2, bx1, by0+16], fill=(100,0,130,255))
    cd.rectangle([bx0, by0+9, bx1, by1+4], fill=(170,0,210,255))
    # Main body
    cd.rectangle([bx0+2, by0, bx1-2, by1], fill=(190,20,200,255))
    # Highlight streak
    cd.rectangle([bx0+6, by0+5, bx0+12, by1-5], fill=(210,60,220,120))
    # Bottom ellipse
    cd.ellipse([bx0, by1-6, bx1, by1+8], fill=(110,0,145,255))
    cd.ellipse([bx0+2, by1-4, bx1-2, by1+6], fill=(130,0,165,255))

    # --- Cap (yellow-green) ---
    cap_col = (220,230,80,255)
    cd.ellipse([bx0-2, by0-20, bx1+2, by0+4], fill=cap_col)
    cd.rectangle([bx0, by0-14, bx1, by0+2], fill=cap_col)
    cd.ellipse([bx0+1, by0-2, bx1-1, by0+10], fill=(170,180,50,255))

    # --- Nozzle ---
    nx = (bx0+bx1)//2
    cd.rectangle([nx-5, by0-30, nx+5, by0-18], fill=(80,0,110,255))
    cd.rectangle([nx-3, by0-32, nx+3, by0-28], fill=(30,30,30,255))
    cd.rectangle([nx-2, by0-38, nx+2, by0-31], fill=(20,20,20,255))

    # --- Black outline ---
    cd.rectangle([bx0,by0,bx1,by1], outline=(10,5,15,255), width=2)
    cd.ellipse([bx0,by1-6,bx1,by1+8], outline=(10,5,15,255), width=2)
    cd.ellipse([bx0-2,by0-20,bx1+2,by0+4], outline=(10,5,15,255), width=2)

    # --- Flame/drop logo (yellow-green) ---
    lx, ly = CW//2, (by0+by1)//2
    # Flame shape: teardrop pointing up
    flame_pts = [
        (lx,    ly-18),   # top tip
        (lx+8,  ly-5),
        (lx+6,  ly+8),
        (lx,    ly+12),
        (lx-6,  ly+8),
        (lx-8,  ly-5),
    ]
    cd.polygon(flame_pts, fill=(225,235,70,255))
    # Inner hook
    cd.line([(lx, ly+6),(lx-4, ly-2),(lx-2, ly-10)], fill=(160,60,180,255), width=2)
    cd.ellipse([lx-3,ly-1,lx+3,ly+5], fill=(160,60,180,255))

    # Rotate
    rotated = can.rotate(angle_deg, expand=True, resample=Image.BICUBIC)

    # Scale to target height
    rw, rh = rotated.size
    scale  = target_h / rh
    new_w  = int(rw * scale)
    new_h  = target_h
    return rotated.resize((new_w, new_h), Image.LANCZOS)

# Pre-render spray can (left: tilted right +35, right: tilted left -35)
can_left  = make_spray_can(target_h=H-8, angle_deg=35)   # nozzle pointing right
can_right = make_spray_can(target_h=H-8, angle_deg=-35)  # nozzle pointing left

CL_W, CL_H = can_left.size
CR_W, CR_H = can_right.size

# Bounce offsets per frame (subtle float animation)
def can_offset(f, phase=0):
    return int(3 * math.sin(f * 0.22 + phase))

# ── HELPER FUNCTIONS (same as before) ────────────────────────────────────────
def draw_base(draw):
    for y in range(H):
        t = y/H
        draw.line([(0,y),(W,y)], fill=(int(6+8*t),int(4+6*t),int(14+20*t)))
    gy0 = int(H*0.62)
    for y in range(gy0,H):
        t = (y-gy0)/(H-gy0)
        draw.line([(0,y),(W,y)], fill=(int(10+12*t),int(6+8*t),int(22+18*t)))

def draw_gas_station(draw):
    cx0=int(W*0.52); cy0=int(H*0.05); ch=int(H*0.20)
    draw.rectangle([cx0,cy0,W,cy0+ch],      fill=(14,10,24))
    draw.rectangle([cx0,cy0,W,cy0+3],       fill=(30,22,50))
    draw.rectangle([cx0,cy0+ch-2,W,cy0+ch], fill=(25,18,42))
    for px2 in [cx0+55,cx0+250,cx0+500,W-50]:
        draw.rectangle([px2,cy0+ch,px2+10,H],    fill=(18,13,30))
        draw.rectangle([px2-2,cy0+ch-3,px2+12,cy0+ch+3],fill=(28,20,46))
    for pump_x in [int(W*0.73),int(W*0.82),int(W*0.91)]:
        py2=int(H*0.32)
        draw.rectangle([pump_x,py2,pump_x+16,H-8],      fill=(13,10,22))
        draw.rectangle([pump_x-3,py2-5,pump_x+19,py2+5],fill=(22,16,38))
        draw.rectangle([pump_x+2,py2+8,pump_x+14,py2+22],fill=(30,15,60))
        draw.rectangle([pump_x+3,py2+9,pump_x+13,py2+21],fill=(50,20,100))
        draw.line([(pump_x+14,py2+28),(pump_x+22,py2+42)],fill=(20,15,30),width=2)
    return cy0, ch

def draw_sign(draw, flicker):
    sx,sy,sw,sh = int(W*0.58),4,155,18
    b = 1.0 if not flicker else random.uniform(0.4,1.0)
    for i in range(10,0,-1):
        a=int(18*(i/10)*b)
        draw.rectangle([sx-i,sy-i,sx+sw+i,sy+sh+i],fill=(a//2,a//3,a*2))
    draw.rectangle([sx,sy,sx+sw,sy+sh],fill=(16,12,35))
    draw.rectangle([sx,sy,sx+sw,sy+2], fill=(50,35,90))
    col=int(140*b)
    draw.text((sx+10,sy+3),"Kwik  Trip",font=font_sign,fill=(col,int(col*0.85),int(col*1.5)))

def draw_lights(draw, cy0, ch, f):
    for idx,(lx,col) in enumerate([(int(W*0.63),(70,55,150)),
                                    (int(W*0.76),(55,90,170)),
                                    (int(W*0.89),(65,80,160))]):
        ly  = cy0+ch
        pulse = 0.75+0.25*math.sin(f*0.18+idx*1.1)
        for r in range(20,0,-2):
            a=int(55*(r/20)**2*pulse)
            draw.ellipse([lx-r,ly-r//3,lx+r,ly+r//2],
                         fill=(min(255,col[0]+a),min(255,col[1]+a),min(255,col[2]+a)))
        for i in range(20,0,-1):
            a=int(26*(i/20)*pulse)
            draw.polygon([(lx-i*4,ly+i*3),(lx,ly),(lx+i*4,ly+i*3)],fill=(a//2,a//3,a*2))

def draw_rain(draw, fi):
    for rx,ry,rl,alp in RAIN_SETS[fi]:
        draw.line([(rx,ry),(rx-1,ry+rl)],fill=(alp,alp,alp+25),width=1)

def draw_puddles(draw, fi):
    for rx,ry,rw,alp in PUDDLE_SETS[fi]:
        draw.line([(rx,ry),(rx+rw,ry)],fill=(alp//2,0,alp*2),width=1)

def draw_person(draw):
    ppx=int(W*0.24); ppy=H
    draw.ellipse([ppx-7,ppy-9,ppx+1,ppy-2],  fill=(165,160,185))
    draw.ellipse([ppx+3,ppy-9,ppx+11,ppy-2], fill=(160,155,180))
    draw.polygon([ppx-7,ppy,ppx-5,ppy-42,ppx+1,ppy-42,ppx+4,ppy],  fill=(9,7,16))
    draw.polygon([ppx+3,ppy,ppx+5,ppy-42,ppx+11,ppy-42,ppx+13,ppy],fill=(11,8,18))
    draw.polygon([ppx-9,ppy-70,ppx+13,ppy-70,ppx+11,ppy-42,ppx-8,ppy-42],fill=(11,8,19))
    draw.ellipse([ppx-9,ppy-90,ppx+13,ppy-68],fill=(13,9,21))
    draw.line([(ppx-9,ppy-64),(ppx-14,ppy-44)],fill=(13,9,21),width=5)
    draw.line([(ppx+11,ppy-64),(ppx+15,ppy-44)],fill=(13,9,21),width=5)

def draw_neon_text(img, reveal_frac, glow_pulse):
    TEXT = "DALTON  LIFE"
    if reveal_frac <= 0:
        return
    draw2 = ImageDraw.Draw(img)
    glow_layer = Image.new("RGB",(W,H),(0,0,0))
    gd = ImageDraw.Draw(glow_layer)
    gs = int(100*glow_pulse)
    for ox,oy in [(-7,0),(7,0),(0,-5),(0,5),(-5,-5),(5,-5),(-5,5),(5,5),(-10,0),(10,0)]:
        gd.text((TX+ox,TY+oy),TEXT,font=font_gothic,fill=(gs,0,min(255,gs*2)))
    gb = glow_layer.filter(ImageFilter.GaussianBlur(radius=5))
    img.paste(Image.blend(img,gb,0.8*glow_pulse))
    draw2 = ImageDraw.Draw(img)
    letters=list(TEXT); cur_x=TX
    revealed=int(len(letters)*reveal_frac)
    for i,ch in enumerate(letters):
        lb=draw2.textbbox((0,0),ch,font=font_gothic)
        lw2=lb[2]-lb[0]
        if i<revealed:
            t_l=i/max(len(letters)-1,1)
            rc=int(180-80*t_l); gc=int(20+20*t_l); bc=int(220+35*t_l)
            for ox,oy in [(-2,0),(2,0),(0,-2),(0,2)]:
                draw2.text((cur_x+ox,TY+oy),ch,font=font_gothic,fill=(150,30,220))
            draw2.text((cur_x,TY),ch,font=font_gothic,fill=(rc,gc,bc))
            if i==revealed-1 and reveal_frac<0.98:
                for dy in range(0,TH,6):
                    if random.random()<0.35:
                        dl=random.randint(3,10)
                        draw2.line([(cur_x+lw2,TY+dy),(cur_x+lw2,TY+dy+dl)],fill=(100,0,200),width=2)
        cur_x+=lw2
    if reveal_frac>=0.98:
        pc=int(80+60*glow_pulse)
        draw2.line([(TX,TY+TH+2),(TX+TW,TY+TH+2)],fill=(pc,0,pc*2),width=1)

def apply_vignette(img):
    for i in range(200):
        t2=((200-i)/200)**1.8; val=int(155*t2)
        for y in range(H):
            p=img.getpixel((i,y))
            img.putpixel((i,y),(max(0,p[0]-val),max(0,p[1]-val),max(0,p[2]-val//2)))
            p2=img.getpixel((W-1-i,y))
            img.putpixel((W-1-i,y),(max(0,p2[0]-val),max(0,p2[1]-val),max(0,p2[2]-val//2)))
    for i in range(16):
        t3=((16-i)/16)**2; val2=int(120*t3)
        for x in range(W):
            p=img.getpixel((x,i))
            img.putpixel((x,i),(max(0,p[0]-val2),max(0,p[1]-val2),max(0,p[2]-val2)))
            p2=img.getpixel((x,H-1-i))
            img.putpixel((x,H-1-i),(max(0,p2[0]-val2),max(0,p2[1]-val2),max(0,p2[2]-val2)))

def apply_grain(img, seed):
    rng=random.Random(seed)
    for _ in range(W*H//18):
        gx3=rng.randint(0,W-1); gy3=rng.randint(0,H-1)
        v=rng.randint(185,255); p=img.getpixel((gx3,gy3))
        img.putpixel((gx3,gy3),tuple(min(255,c+v//32) for c in p))

# ── BUILD FRAMES ─────────────────────────────────────────────────────────────
frames_out = []

for f in range(FRAMES):
    img  = Image.new("RGB",(W,H),(5,3,12))
    draw = ImageDraw.Draw(img)

    draw_base(draw)
    cy0, ch = draw_gas_station(draw)
    draw_puddles(draw, f % FRAMES)
    draw_sign(draw, f % 7 == 3)
    draw_lights(draw, cy0, ch, f)
    draw_rain(draw, f % FRAMES)
    draw_person(draw)

    reveal_frac = 0.0 if f<7 else (((f-7)/21) if f<=28 else 1.0)
    glow_pulse  = 0.6+0.4*math.sin(f*0.28)
    draw_neon_text(img, reveal_frac, glow_pulse)

    # ── PASTE SPRAY CANS ─────────────────────────────────────────────────────
    bob = can_offset(f, 0)

    # LEFT spray can (nozzle pointing right/inward)
    left_x = 4
    left_y = (H - CL_H) // 2 + bob
    img.paste(can_left,  (left_x, left_y), can_left)

    # RIGHT spray can (nozzle pointing left/inward, mirrored)
    right_x = W - CR_W - 4
    right_y = (H - CR_H) // 2 + can_offset(f, math.pi)  # opposite phase
    img.paste(can_right, (right_x, right_y), can_right)

    apply_vignette(img)
    apply_grain(img, f*19)

    frames_out.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    print(f"  Frame {f+1}/{FRAMES}", end="\r")

print()

out = r"C:\Users\Jonathan Rosa\OneDrive\Desktop\APP MIO\banner_cinematic_anim.gif"
frames_out[0].save(
    out, save_all=True, append_images=frames_out[1:],
    loop=0, duration=75, optimize=True
)
print(f"GIF guardado -> {out}  ({FRAMES} frames, {W}x{H})")
