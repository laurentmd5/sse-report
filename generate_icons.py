from PIL import Image
import os

source_img = 'Icone.jpeg'
if not os.path.exists(source_img):
    print('Icone.jpeg not found!')
    exit(1)

img = Image.open(source_img).convert('RGBA')

# Web Favicon
img.save('app/static/favicon.ico', format='ICO', sizes=[(32, 32)])
print('Favicon generated.')

# Android Icons
sizes = {
    'mdpi': 48,
    'hdpi': 72,
    'xhdpi': 96,
    'xxhdpi': 144,
    'xxxhdpi': 192
}

for density, size in sizes.items():
    res_dir = f'android-app/app/src/main/res/mipmap-{density}'
    os.makedirs(res_dir, exist_ok=True)
    
    # ic_launcher.png
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(os.path.join(res_dir, 'ic_launcher.png'))
    
    # ic_launcher_round.png (we can just use the same image, or make it round)
    # Since it's a white background logo, square is fine, Android handles rounding if we don't have a specific round icon, but we MUST overwrite the default round icon too so it doesn't show the default green Android head.
    resized.save(os.path.join(res_dir, 'ic_launcher_round.png'))
    
print('Android icons generated.')
