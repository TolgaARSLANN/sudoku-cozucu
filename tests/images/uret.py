"""Test ekran görüntülerini üretir (ekran_1.jpg, ekran_2.jpg): sudoku sitelerinin ekran görüntülerine
benzeyen sentetik görseller. Gerçek ekran görüntüsü kullanılmadı; telif sorunu yok.

    python tests/images/uret.py      (Windows yazı tipleri gerekir; üretilmiş halleri depoda)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent)]
from test_pipeline import SCREENSHOTS  # noqa: E402


def render(puzzle, size, cell, thin, thick, thin_w, thick_w, digit_color, font, font_size):
    """cell: (genişlik, yükseklik). Izgara görselden büyükse sağ ve alt kenar kesilir (kırpılmış ekran görüntüsü)."""
    cw, ch = cell
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font, font_size)
    for k in range(10):
        color, w = (thick, thick_w) if k % 3 == 0 else (thin, thin_w)
        d.line([(k * cw, 0), (k * cw, ch * 9)], fill=color, width=w)
        d.line([(0, k * ch), (cw * 9, k * ch)], fill=color, width=w)
    for i, digit in enumerate(puzzle):
        if digit != "0":
            r, c = divmod(i, 9)
            d.text((c * cw + cw / 2, r * ch + ch / 2), digit, fill=digit_color, font=f, anchor="mm")
    return img


if __name__ == "__main__":
    # Gri, ince çizgili site görünümü
    render(SCREENSHOTS["ekran_1.jpg"], (360, 360), (39.8, 39.8), (200, 200, 200), (150, 150, 150), 1, 3,
           (85, 85, 85), r"C:\Windows\Fonts\segoeui.ttf", 21).save(HERE / "ekran_1.jpg", quality=80)
    # Kalın siyah kutu çizgileri, hafif dikdörtgen hücreler; sağ ve alt kenar kesilmiş
    render(SCREENSHOTS["ekran_2.jpg"], (391, 377), (43.4, 41.9), (170, 170, 170), (0, 0, 0), 1, 4,
           (0, 0, 0), r"C:\Windows\Fonts\arial.ttf", 19).save(HERE / "ekran_2.jpg", quality=80)
