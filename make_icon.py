# Генератор icon.ico / icon.png. Запускать один раз.

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


COLOR_BG_TOP = (12, 24, 56)
COLOR_BG_BOT = (8, 60, 90)
COLOR_H = (255, 255, 255)
COLOR_ACCENT = (52, 211, 200)
COLOR_GLOW = (52, 211, 200, 70)


def _draw_gradient_rounded(size: int, radius: int, top: tuple, bot: tuple) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = grad.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b, 255)

    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    img.paste(grad, (0, 0), mask=mask)
    return img


def make_icon(size: int) -> Image.Image:
    big = size * 4  # рендер в 4x для антиалиасинга

    radius = int(big * 0.18)
    img = _draw_gradient_rounded(big, radius, COLOR_BG_TOP, COLOR_BG_BOT)
    d = ImageDraw.Draw(img, "RGBA")

    bar_w = int(big * 0.16)
    edge_x = int(big * 0.22)
    edge_y = int(big * 0.20)
    cb_y = int(big * 0.46)
    cb_h = int(big * 0.13)

    d.rectangle((edge_x, edge_y, edge_x + bar_w, big - edge_y), fill=COLOR_H)
    d.rectangle((big - edge_x - bar_w, edge_y, big - edge_x, big - edge_y), fill=COLOR_H)
    d.rectangle((edge_x, cb_y, big - edge_x, cb_y + cb_h), fill=COLOR_H)

    tri_size = int(big * 0.32)
    tri_inset = int(big * 0.06)
    tri = [
        (big - tri_inset, tri_inset),
        (big - tri_inset, tri_inset + tri_size),
        (big - tri_inset - tri_size, tri_inset),
    ]
    d.polygon(tri, fill=COLOR_ACCENT)

    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.polygon(tri, fill=COLOR_GLOW)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=int(big * 0.025)))
    img = Image.alpha_composite(img, glow)

    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [make_icon(s) for s in sizes]

    ico_path = Path(__file__).parent / "icon.ico"
    images[0].save(
        str(ico_path), format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"saved {ico_path}")

    png_path = Path(__file__).parent / "icon.png"
    images[-1].save(str(png_path), format="PNG")
    print(f"saved {png_path}")


if __name__ == "__main__":
    main()
