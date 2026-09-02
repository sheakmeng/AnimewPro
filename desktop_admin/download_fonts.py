import os
import requests
import re

fonts_dir = r"c:\Users\sheakmeng\Desktop\New folder\desktop_admin\fonts"
os.makedirs(fonts_dir, exist_ok=True)

# Direct TTF links from Google Fonts GitHub repository
fonts = [
    ("KantumruyPro-Regular.ttf", "https://github.com/google/fonts/raw/main/ofl/kantumruypro/static/KantumruyPro-Regular.ttf"),
    ("KantumruyPro-Bold.ttf", "https://github.com/google/fonts/raw/main/ofl/kantumruypro/static/KantumruyPro-Bold.ttf"),
    ("KantumruyPro-SemiBold.ttf", "https://github.com/google/fonts/raw/main/ofl/kantumruypro/static/KantumruyPro-SemiBold.ttf"),
    ("Koulen.ttf", "https://github.com/google/fonts/raw/main/ofl/koulen/Koulen-Regular.ttf"),
    ("Battambang-Regular.ttf", "https://github.com/google/fonts/raw/main/ofl/battambang/Battambang-Regular.ttf"),
    ("Battambang-Bold.ttf", "https://github.com/google/fonts/raw/main/ofl/battambang/Battambang-Bold.ttf"),
    ("Siemreap.ttf", "https://github.com/google/fonts/raw/main/ofl/siemreap/Siemreap.ttf")
]

# Try getting variable font from Google Fonts GitHub if static isn't in that exact folder
var_kantumruy = "https://raw.githubusercontent.com/googlefonts/kantumruy-pro/main/fonts/ttf/KantumruyPro-Regular.ttf"
var_kantumruy_bold = "https://raw.githubusercontent.com/googlefonts/kantumruy-pro/main/fonts/ttf/KantumruyPro-Bold.ttf"
var_kantumruy_semibold = "https://raw.githubusercontent.com/googlefonts/kantumruy-pro/main/fonts/ttf/KantumruyPro-SemiBold.ttf"

extra_fonts = [
    ("KantumruyPro-Regular.ttf", var_kantumruy),
    ("KantumruyPro-Bold.ttf", var_kantumruy_bold),
    ("KantumruyPro-SemiBold.ttf", var_kantumruy_semibold),
]

for name, url in fonts + extra_fonts:
    dest = os.path.join(fonts_dir, name)
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"Downloaded {name} ({len(r.content)/1024:.1f} KB)")
    except Exception as e:
        print(f"Error {name}: {e}")

print("Available font files in desktop_admin/fonts:")
for f in os.listdir(fonts_dir):
    print(" -", f)
