from PIL import Image, ImageDraw
import os

src = r'C:\Users\Administrator\TuringClaw\gui\chinatelecom.jpeg'
out_dir = r'C:\Users\Administrator\TuringClaw\ct_icons'
try:
    os.makedirs(out_dir, exist_ok=True)
except:
    pass

img = Image.open(src).convert("RGBA")

variants = [
    ("logo_main",    0,   0,   0,   "Main blue logo"),
    ("logo_green", -50,  80, -80,   "Green - Ollama"),
    ("logo_red",   150, -60, -80,   "Red - error"),
    ("logo_yellow", 80,  40,-120,   "Yellow - notice"),
    ("logo_purple", 60, -40,  60,   "Purple - settings"),
    ("logo_cyan", -100,  60,  60,   "Cyan - status"),
    ("logo_orange",120,  20,-100,   "Orange - stats"),
    ("logo_white", 200, 130,  90,   "White - demo"),
]

def colorize(img_in, rs, gs, bs):
    r, g, b, a = img_in.split()
    def shift(c, s):
        lut = [max(0, min(255, i + s)) for i in range(256)]
        return c.point(lut)
    return Image.merge("RGBA", (shift(r, rs), shift(g, gs), shift(b, bs), a))

for name, rs, gs, bs, desc in variants:
    colored = colorize(img, rs, gs, bs)
    p = os.path.join(out_dir, f"{name}.png")
    colored.save(p)
    print(f"OK: {name}")

print(f"\nSaved to: {out_dir}")
