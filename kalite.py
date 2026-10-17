"""Fotoğraf kalite kontrolü: okuma başarısız olunca olası sebebi ve ne yapılacağını söyler.

Eşikler ölçüm setindeki 80 gerçek fotoğrafa bakılarak seçildi. Keskinlik tek başına başarıyı
belirlemiyor (eski telefonların çözülen fotoğrafları da bulanık), bu yüzden uyarılar sadece
çözüm başarısız olduğunda gösterilir.
"""
import cv2
import numpy as np

from vision import warp_grid

MIN_SHARPNESS = 60    # Laplace varyansı; çözülemeyen bulanık fotoğraflar 5–54, diğer başarısızlar 100+
MIN_GRID_SIDE = 250   # piksel; ölçüm setindeki en küçük ızgara 325 px
MIN_BRIGHTNESS = 80   # kağıdın ortanca parlaklığı; ölçüm setindeki en karanlık 104
MAX_GLARE = 0.02      # patlamış beyaz piksel oranı (ölçüm setinde hep 0)
WHITE_PAPER = 230     # kağıt zaten bembeyazsa (ekran görüntüsü) parlama aranmaz

WARNINGS = {
    "bulanik": "Fotoğraf bulanık ya da çözünürlüğü düşük görünüyor. Kamerayı sabit tutup netleşmesini "
               "bekle ya da sudokuya biraz yaklaş.",
    "kucuk": "Izgara fotoğrafta çok küçük. Sudokuya yaklaşıp kadrajı ızgarayla doldur.",
    "karanlik": "Fotoğraf çok karanlık. Daha aydınlık bir yerde çek.",
    "parlama": "Fotoğrafta parlama var. Işık kağıttan doğrudan yansımasın diye açıyı biraz değiştir.",
}


def check_quality(img, corners=None):
    """Olası sorunların listesi: ["bulanik", ...]. Izgara bulunduysa sadece ızgaraya bakılır."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if corners is not None:
        region = warp_grid(gray, corners)
        side = np.mean([np.linalg.norm(corners[i] - corners[(i + 1) % 4]) for i in range(4)])
    else:  # ızgara yoksa tüm fotoğraf, sabit genişlikte (keskinlik çözünürlüğe bağlı)
        region = cv2.resize(gray, None, fx=640 / gray.shape[1], fy=640 / gray.shape[1],
                            interpolation=cv2.INTER_AREA)
        side = None

    problems = []
    if cv2.Laplacian(region, cv2.CV_64F).var() < MIN_SHARPNESS:
        problems.append("bulanik")
    if side is not None and side < MIN_GRID_SIDE:
        problems.append("kucuk")
    paper = np.median(region)
    if paper < MIN_BRIGHTNESS:
        problems.append("karanlik")
    elif paper < WHITE_PAPER and (region >= 250).mean() > MAX_GLARE:
        problems.append("parlama")
    return problems
