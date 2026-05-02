from PIL import Image
img = Image.open(r'C:\Users\Administrator\TuringClaw\gui\chinatelecom.jpeg')
print(f"Size: {img.size}, Mode: {img.mode}")
# Get dominant colors
img_small = img.resize((50, 50))
pixels = list(img_small.getdata())
# Sample some pixels
for i in [0, 100, 500, 1000, 1500, 2000, 2499]:
    if i < len(pixels):
        print(f"Pixel {i}: {pixels[i]}")
