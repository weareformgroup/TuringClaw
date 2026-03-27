"""
Generate colored China Telecom logo variants for TuringClaw GUI icons.
"""
from PIL import Image, ImageEnhance, ImageFilter
import os

src = r'C:\Users\Administrator\TuringClaw\gui\chinatelecom.jpeg'
out_dir = r'C:\Users\Administrator\TuringClaw\gui\icons'
os.makedirs(out_dir, exist_ok=True)

img = Image.open(src).convert("RGBA")

# Color variants: (name, R_shift, G_shift, B_shift, description)
variants = [
    ("main",       0,    0,    0,   "Original blue - main logo"),
    ("green",    -50,   80,  -80,   "Green - Ollama / local"),
    ("red",      150,  -60,  -80,   "Red - error / warning"),
    ("yellow",    80,   40, -120,   "Yellow - system notice"),
    ("purple",    60,  -40,   60,   "Purple - settings"),
    ("cyan",    -100,   60,   60,   "Cyan - status / online"),
    ("orange",   120,   20, -100,   "Orange - stats"),
    ("white",    200,  130,   90,   "White/light - demo mode"),
]

def colorize(img, r_shift, g_shift, b_shift):
    """Shift RGB channels to create a color variant."""
    r, g, b, a = img.split()
    
    def shift_channel(channel, shift):
        lut = [max(0, min(255, i + shift)) for i in range(256)]
        return channel.point(lut)
    
    r = shift_channel(r, r_shift)
    g = shift_channel(g, g_shift)
    b = shift_channel(b, b_shift)
    return Image.merge("RGBA", (r, g, b, a))

for name, rs, gs, bs, desc in variants:
    colored = colorize(img, rs, gs, bs)
    
    # Save full size (for toolbar logo)
    out_path = os.path.join(out_dir, f"logo_{name}.png")
    colored.save(out_path)
    
    # Save small size (32x32 for icons)
    small = colored.resize((32, 32), Image.LANCZOS)
    small.save(os.path.join(out_dir, f"icon_{name}.png"))
    
    # Save medium size (48x48 for buttons)
    medium = colored.resize((48, 48), Image.LANCZOS)
    medium.save(os.path.join(out_dir, f"btn_{name}.png"))
    
    print(f"[OK] Generated {name}: {desc}")

print(f"\nAll icons saved to: {out_dir}")
