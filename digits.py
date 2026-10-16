"""Basılı rakam tanıma: Windows fontlarından sentetik veri üretir, k-NN ile sınıflandırır."""
import glob
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE = 28
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "digits_data.npz")
# Rakam yerine sembol çizen fontlar
SKIP = ("sym", "wing", "webd", "marlett", "mdl2", "icons", "emoji", "holo", "bss", "ext")


def normalize(binary):
    """Siyah zemin üzerindeki beyaz rakamı kırpıp 28x28'e ortalar, düz vektör döndürür."""
    ys, xs = np.nonzero(binary)
    if len(xs) == 0:
        return None
    crop = (binary[ys.min():ys.max() + 1, xs.min():xs.max() + 1] > 0).astype(np.uint8) * 255
    h, w = crop.shape
    scale = 20 / max(h, w)
    crop = cv2.resize(crop, (max(1, round(w * scale)), max(1, round(h * scale))),
                      interpolation=cv2.INTER_AREA)
    out = np.zeros((SIZE, SIZE), np.float32)
    h, w = crop.shape
    y, x = (SIZE - h) // 2, (SIZE - w) // 2
    out[y:y + h, x:x + w] = crop
    return (out / 255).ravel()


def _render(font, digit):
    img = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(img).text((30, 10), str(digit), fill=255, font=font)
    return np.array(img)


def _variants(img):
    """Hafif döndürme ve kalınlık farklarıyla veri çoğaltma."""
    kernel = np.ones((3, 3), np.uint8)
    center = (img.shape[1] / 2, img.shape[0] / 2)
    for angle in (-6, 0, 6):
        rot = cv2.warpAffine(img, cv2.getRotationMatrix2D(center, angle, 1), img.shape[::-1])
        yield rot
    yield cv2.erode(img, kernel)
    yield cv2.dilate(img, kernel)
    # Gerçek fotoğraf: düşük çözünürlük + bulanıklık; eşik değeri çizgi kalınlığını belirler
    small = cv2.resize(img, (30, 30), interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(small, (5, 5), 0)
    for level in (60, 120):
        yield cv2.resize(((blurred > level) * 255).astype(np.uint8), img.shape[::-1],
                         interpolation=cv2.INTER_NEAREST)


def build_dataset():
    fonts = glob.glob(r"C:\Windows\Fonts\*.ttf") + glob.glob(r"C:\Windows\Fonts\*.otf")
    X, y = [], []
    used = 0
    for path in fonts:
        if any(s in os.path.basename(path).lower() for s in SKIP):
            continue
        try:
            font = ImageFont.truetype(path, 70)
            glyphs = [_render(font, d) for d in range(1, 10)]
        except OSError:  # bozuk ya da desteklenmeyen font
            continue
        vecs = [normalize(g > 127) for g in glyphs]
        # Rakamı olmayan ya da her rakamı aynı kutu olarak çizen fontları ele
        if any(v is None for v in vecs) or len({v.tobytes() for v in vecs}) < 9:
            continue
        used += 1
        for d, g in zip(range(1, 10), glyphs):
            for v in _variants(g):
                vec = normalize(v > 127)
                if vec is not None:
                    X.append(vec)
                    y.append(d)
    # Değerler k/255 biçiminde: 1 baytlık tamsayı olarak kayıpsız saklanır (float32'ye göre 4 kat küçük)
    np.savez_compressed(DATA_FILE, X=np.round(np.array(X) * 255).astype(np.uint8), y=np.array(y, np.uint8))
    print(f"Veri seti hazır: {used} font, {len(X)} örnek")


class DigitClassifier:
    def __init__(self):
        if not os.path.exists(DATA_FILE):
            build_dataset()
        data = np.load(DATA_FILE)
        order = np.argsort(data["y"], kind="stable")  # örnekler rakama göre gruplansın
        self.X = data["X"][order].astype(np.float32) / 255
        self.sq = (self.X ** 2).sum(1)
        self.starts = np.searchsorted(data["y"][order], np.arange(1, 10))  # her rakamın ilk örneği

    def class_distances(self, vecs):
        """Her vektör için 1-9 rakamlarının her birine en yakın örneğin uzaklığı: (n, 9)."""
        V = np.asarray(vecs, np.float32)
        dist2 = (V ** 2).sum(1)[:, None] + self.sq[None, :] - 2 * V @ self.X.T
        # Karekök artan bir fonksiyon: önce her rakamın en küçüğünü bul, kökü sadece 9 değerde al
        return np.sqrt(np.maximum(np.minimum.reduceat(dist2, self.starts, axis=1), 0))


if __name__ == "__main__":
    build_dataset()
