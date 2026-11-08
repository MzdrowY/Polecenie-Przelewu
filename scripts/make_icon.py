"""Generuj assets/icon.ico z assets/icon.icns lub PNG (wymaga Pillow)."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent.parent
src = root / "assets" / "icon.icns"
out = root / "assets" / "icon.ico"
if not src.exists():
    # fallback: szukaj PNG 1024
    pngs = list((root / "assets").glob("*.png"))
    if not pngs:
        raise SystemExit("Brak źródła ikony.")
    src = pngs[0]

img = Image.open(src)
img.save(out, format="ICO", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("Zapisano", out)