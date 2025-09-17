from PIL import Image
from pathlib import Path


def main():
    static_dir = Path(__file__).resolve().parents[1] / "static"
    logo_path = static_dir / "logo.png"
    if not logo_path.exists():
        raise SystemExit("No se encontró static/logo.png. Asegurate de renombrar el archivo correctamente.")

    src = Image.open(logo_path).convert("RGBA")
    width, height = src.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    square = src.crop((left, top, left + side, top + side))

    # PNG grande para compatibilidad
    fav_png = square.resize((256, 256), Image.LANCZOS)
    fav_png.save(static_dir / "favicon.png")

    # ICO estándar 32x32
    fav_ico = square.resize((32, 32), Image.LANCZOS)
    fav_ico.save(static_dir / "favicon.ico")

    print("Listo: generado static/favicon.png y static/favicon.ico")


if __name__ == "__main__":
    main()


