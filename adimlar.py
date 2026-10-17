"""'Nasıl gördüm?' paneli: görüntü işlemenin ara sonuçlarını açıklamalı görsellere çevirir."""
import cv2
import numpy as np

from vision import CELL, UNSURE_MARGIN

FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN, AMBER, ORANGE, GRAY = (60, 160, 40), (0, 170, 240), (10, 100, 230), (150, 150, 150)  # BGR


def _fit(img, width=900):
    scale = min(1.0, width / img.shape[1])
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img, scale


def _label(img, text, org, color, size=0.6):
    """Okunaklı olsun diye arka planı dolu küçük etiket."""
    (w, h), base = cv2.getTextSize(text, FONT, size, 2)
    x, y = int(org[0]), int(org[1])
    cv2.rectangle(img, (x, y - h - 6), (x + w + 8, y + base), color, -1)
    cv2.putText(img, text, (x + 4, y - 3), FONT, size, (255, 255, 255), 2, cv2.LINE_AA)


def _ink_on_paper(binary):
    """Siyah zemin üzerine beyaz mürekkep yerine, kağıttaki gibi beyaz zemin üstüne siyah."""
    return cv2.cvtColor(255 - binary, cv2.COLOR_GRAY2BGR)


def build_steps(img, trace, result):
    """Döner: [(başlık, açıklama, görsel)]. Izgara bulunamadıysa ilk iki adım."""
    steps = [("Siyah-beyaz görüntü",
              "Her piksel kendi çevresiyle karşılaştırılıp koyu ya da açık sayıldı (uyarlamalı eşikleme). "
              "Böylece gölge ve ışık farkı olan fotoğraflarda da çizgiler ve rakamlar ayrışır.",
              _ink_on_paper(trace["threshold"]))]

    view, scale = _fit(img.copy())
    chosen = trace.get("chosen")
    for quad, score in sorted(trace["quads"], key=lambda q: q[1]):  # seçilen en üstte çizilsin
        selected = chosen is not None and np.allclose(quad, chosen)
        color = GREEN if selected else (AMBER if score >= 0.4 else GRAY)
        pts = (quad * scale).astype(np.int32)
        cv2.polylines(view, [pts], True, color, 4 if selected else 2, cv2.LINE_AA)
        _label(view, f"{score:.2f}", pts[0] + (6, 28), color)
    if chosen is None:
        best = max((s for _, s in trace["quads"]), default=None)
        text = ("Hiçbir dörtgen ızgara testini geçemedi"
                + (f" (en iyi puan {best:.2f})." if best is not None else "; hiç dörtgen bulunamadı.")
                + " Izgaranın tamamı kadrajda ve net olmalı.")
    else:
        text = (f"{len(trace['quads'])} dörtgen bulundu. Her biri düzleştirilip iç çizgilerin 1/9 aralıklarla "
                "durup durmadığına göre puanlandı (1.00 = kusursuz ızgara). Yeşil: seçilen, sarı: testi geçen, "
                "gri: geçemeyen.")
    steps.append(("Izgara adayları", text, view))
    if chosen is None:
        return steps

    warped = cv2.cvtColor(trace["warped"], cv2.COLOR_GRAY2BGR)
    steps.append(("Düzleştirilmiş tahta",
                  "Seçilen dörtgen perspektif dönüşümüyle kareye çevrildi. Fotoğraf yan ya da ters çekilmiş "
                  "olabileceği için 4 yön denendi; rakamların en net okunduğu yön seçildi.",
                  warped))

    ink = _ink_on_paper(trace["ink"])
    for x, y, w, h in trace["boxes"]:
        cv2.rectangle(ink, (x - 2, y - 2), (x + w + 2, y + h + 2), GREEN, 2)
    steps.append(("Izgara çizgileri silindi",
                  "Hücre sınırlarının üstündeki, hücre boyunda düz çizgiler silindi. Hücrenin ortasındaki uzun "
                  "çizgiler korunur: büyük yazılmış bir 1'in ya da 7'nin gövdesi olabilir. "
                  f"Kalan parçalardan rakam boyutunda olan {len(trace['boxes'])} tanesi bulundu (yeşil kutular).",
                  ink))

    read = warped.copy()
    unsure = 0
    for i, dist in trace["scores"].items():
        r, c = divmod(i, 9)
        order = np.argsort(dist)
        digit = int(order[0]) + 1
        if i in result.corrected:
            color, text = ORANGE, f"{digit}>{result.board[i]}"
        elif dist[order[1]] - dist[order[0]] < UNSURE_MARGIN:
            color, text = AMBER, f"{digit}?"
            unsure += 1
        else:
            color, text = GREEN, str(digit)
        cv2.rectangle(read, (c * CELL + 2, r * CELL + 2), ((c + 1) * CELL - 2, (r + 1) * CELL - 2), color, 2)
        _label(read, text, (c * CELL + 3, r * CELL + 17), color, size=0.45)
    text = (f"Her rakam, bilgisayardaki yazı tiplerinden üretilen 7162 örnekle karşılaştırıldı. "
            f"Yeşil: emin, sarı: ilk iki tahmin birbirine yakın ({unsure} rakam)")
    if result.corrected:
        text += f", turuncu: sudoku kurallarına göre düzeltilen ({len(result.corrected)} rakam)"
    steps.append(("Okunan rakamlar", text + ".", read))
    return steps
