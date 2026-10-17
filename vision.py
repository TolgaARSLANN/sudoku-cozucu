"""Görüntü işleme: ızgarayı bul, rakamları oku, çözümü görüntünün üstüne çiz."""
from dataclasses import dataclass, field
from io import BytesIO
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from digits import normalize
from solver import solve_unique

WARP = 450
CELL = WARP // 9
SQUARE = np.float32([[0, 0], [WARP, 0], [WARP, WARP], [0, WARP]])
FONT = cv2.FONT_HERSHEY_SIMPLEX


def load_image(path):
    """cv2.imread Windows'ta Türkçe karakterli yolları okuyamaz; baytlardan çözüyoruz."""
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)


def save_image(path, img):
    cv2.imencode(".jpg", img)[1].tofile(path)  # imwrite da Türkçe karakterli yollara yazamaz


def order_corners(pts):
    s = pts.sum(1)
    d = np.diff(pts, axis=1).ravel()  # y - x
    return np.float32([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]])


def grid_score(th, quad, size=270):
    """Dörtgeni düzleştirip iç çizgilerin 1/9 aralıklarla gerçekten orada olup olmadığını ölçer (0-1)."""
    dst = np.float32([[0, 0], [size, 0], [size, size], [0, size]])
    flat = cv2.warpPerspective(th, cv2.getPerspectiveTransform(quad, dst), (size, size)) > 0
    step, win = size // 9, 3
    peaks = []
    for profile in (flat.mean(1), flat.mean(0)):  # satır ve sütun boyunca koyu piksel oranı
        for k in range(1, 9):
            peaks.append(profile[k * step - win:k * step + win + 1].max())
    return float(np.mean(peaks))


def find_grid(gray, trace=None):
    """Sudoku ızgarasının köşelerini bulur: sol-üst, sağ-üst, sağ-alt, sol-alt.

    trace sözlüğü verilirse "Nasıl gördüm?" paneli için ara sonuçlar ona yazılır.
    """
    scale = min(1.0, 640 / gray.shape[1])  # hız için küçük çözünürlükte ara
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 11, 2)
    # Bulanık fotoğraflarda ince ızgara çizgileri eşiklemede kesik kesik kalır ve ızgara kapalı bir
    # dörtgen oluşturmaz. Hafifçe kalınlaştırılmış görüntüden de aday üretilir; kopukluklar kapanır.
    thickened = cv2.dilate(th, np.ones((3, 3), np.uint8))
    candidates = []  # ızgara testini geçenler: (alan, skor, köşeler)
    scored = []      # puanlanan tüm dörtgenler (panelde gösterilir): (köşeler, skor)
    for source in (th, thickened):
        found_in_th = [q * scale for q, _ in scored]
        contours, _ = cv2.findContours(source, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            if cv2.contourArea(c) < gray.size * 0.02:
                break
            # Dış çerçeve yer yer kopuk olabilir; dış bükey zarf yine de temiz bir dörtgen verir
            hull = cv2.convexHull(c)
            if cv2.contourArea(hull) < gray.size * 0.05:
                continue
            approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
            if len(approx) != 4:
                continue
            quad = order_corners(approx.reshape(4, 2).astype(np.float32))
            # Kalınlaştırılmış görüntü sadece yeni dörtgen getirsin: aynı ızgaranın 1 px büyük kopyası
            # "en büyük kazanır" kuralında asıl adayı geçip köşeleri kaydırmasın
            if source is thickened and any(np.abs(quad - q).max() < 5 for q in found_in_th):
                continue
            score = grid_score(th, quad)  # puan hep asıl görüntüde: iki kaynağın adayları karşılaştırılabilsin
            scored.append((quad / scale, score))
            if score >= 0.4:
                candidates.append((cv2.contourArea(hull), score, quad))
    if trace is not None:
        trace["threshold"], trace["quads"] = th, scored
    if not candidates:
        return None
    # 1) En iyi skora yakın olanların en büyüğü: sayfadaki küçük "dünkü çözüm" ızgarası asıl bulmacaya yenilir.
    top = max(score for _, score, _ in candidates)
    area = max(a for a, score, _ in candidates if score >= top - 0.1)
    # 2) Neredeyse aynı boydakiler arasında en yüksek skor: ızgaraya çok yakın bir kağıt/ekran kenarı
    #    da yüksek skor alabilir ama gerçek ızgara her zaman daha iyi hizalıdır.
    _, _, quad = max((c for c in candidates if c[0] >= 0.8 * area), key=lambda c: c[1])
    return quad / scale


def find_digits(warped_gray, trace=None):
    """Düzleştirilmiş tahtadaki rakamları bulur: {hücre indeksi: rakam maskesi}.

    Hücre sınırlarına körü körüne güvenmez: köşeler biraz kaymışsa ya da sayfa kıvrıksa rakam
    hücresinin kenarına dayanabilir. Bunun yerine tüm tahtada rakam boyutundaki parçaları bulur
    ve her birini merkezinin düştüğü hücreye atar.
    """
    th = cv2.adaptiveThreshold(cv2.GaussianBlur(warped_gray, (5, 5), 0), 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    # Izgara çizgilerini sil: hiçbir rakamda hücre boyuna yakın düz bir çizgi yoktur
    length = int(CELL * 0.8)
    h_lines = cv2.morphologyEx(th, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (length, 1)))
    v_lines = cv2.morphologyEx(th, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, length)))
    ink = th & ~cv2.dilate(h_lines | v_lines, np.ones((3, 3), np.uint8))
    # Bulanıklıktan kopmuş rakam parçaları birleşsin diye hafifçe kalınlaştırıp etiketle
    n, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(ink, np.ones((3, 3), np.uint8)))
    digits = {}
    min_area = 0.03 * CELL * CELL
    for i in range(1, n):
        x, y, w, h, blob_area = stats[i]
        # Ucuz kontroller maskeden önce: yüzlerce minik leke için maske hesaplanmasın.
        # Kalınlaştırılmış parçanın alanı, içindeki mürekkep alanından hep büyüktür.
        if not (0.3 * CELL <= h <= 0.95 * CELL and w <= 0.9 * CELL and blob_area >= min_area):
            continue  # leke, gölge ya da rakam boyutunda olmayan şey
        cx, cy = x + w / 2, y + h / 2
        if w < 0.4 * h and min(cx % CELL, CELL - cx % CELL) < 0.15 * CELL:
            continue  # silinemeyen çizgi parçası: hücre sınırının üstünde duran ince dikey şerit
        mask = (labels[y:y + h, x:x + w] == i) & (ink[y:y + h, x:x + w] > 0)
        area = int(mask.sum())
        if area < min_area:
            continue
        idx = int(cy // CELL) * 9 + int(cx // CELL)
        if idx not in digits or area > digits[idx][0]:
            digits[idx] = (area, mask, (x, y, w, h))
    if trace is not None:
        trace["ink"], trace["boxes"] = ink, [box for _, _, box in digits.values()]
    return {i: mask.astype(np.uint8) * 255 for i, (_, mask, _) in digits.items()}


def warp_grid(gray, corners):
    return cv2.warpPerspective(gray, cv2.getPerspectiveTransform(corners, SQUARE), (WARP, WARP))


def read_board(warped_gray, clf):
    """Okunan tahta, hücre başına 1-9 rakamlarına uzaklıklar ve ortalama tanıma mesafesi (düşük = emin)."""
    digits = find_digits(warped_gray)
    board = [0] * 81
    if not digits:
        return board, {}, float("inf")
    idxs = list(digits)
    dists = clf.class_distances([normalize(digits[i]) for i in idxs])
    scores = dict(zip(idxs, dists))
    for i, d in scores.items():
        board[i] = int(d.argmin()) + 1
    return board, scores, float(dists.min(1).mean())


def read_board_any_rotation(gray, corners, clf):
    """Fotoğraf yan ya da ters çekilmiş olabilir: 4 yönü dener, rakamların en net okunduğunu seçer.

    Köşeleri kaydırmak ızgarayı 90° döndürmekle aynıdır; çözüm de aynı köşelerle doğru yönde çizilir.
    """
    best = None
    for k in range(4):
        rotated = np.roll(corners, -k, axis=0)
        board, scores, dist = read_board(warp_grid(gray, rotated), clf)
        if best is None or dist < best[3]:
            best = (rotated, board, scores, dist)
    return best[:3]


def try_solve(board):
    """17'den az ipucu varsa çözüm tek olamaz; büyük ihtimalle rakamlar okunamamıştır."""
    if sum(1 for v in board if v) < 17:
        return None
    return solve_unique(board)


UNSURE_MARGIN = 0.5  # 1. ve 2. tahmin bu kadar yakınsa rakamdan emin değiliz


def unsure_cells(scores):
    return sorted(i for i, d in scores.items() if np.partition(d, 1)[1] - d.min() < UNSURE_MARGIN)


def correct_and_solve(board, scores, max_cost=UNSURE_MARGIN, max_options=10):
    """Tahta çözülemiyorsa okuma hatalarını sudoku kurallarıyla düzeltmeyi dener.

    Sınıflandırıcının 2. ve 3. tahminleri, 1. tahmine ne kadar uzak olduklarına göre "maliyetli"
    değişikliklerdir. Önce tek, sonra iki değişiklik en ucuzdan başlayarak denenir; bir değişiklik
    ancak bulmacayı tek çözümlü yapıyorsa kabul edilir. Sadece emin olunmayan hücreler değişebilir:
    birden çok hata varken emin okunmuş bir rakamı değiştirmek tutarlı ama yanlış bir tahta
    üretebiliyor (gerçek fotoğraflarda görüldü).
    Döner: (çözüm, kullanılan tahta, {düzeltilen hücre: ilk okunan rakam}); çözülemezse çözüm None.
    """
    solution = try_solve(board)
    if solution:
        return solution, board, {}
    options = []
    for i, d in scores.items():
        order = np.argsort(d)
        for alt in order[1:3]:
            cost = float(d[alt] - d[order[0]])
            if cost < max_cost:
                options.append((cost, i, int(alt) + 1))
    options = sorted(options)[:max_options]
    pairs = sorted(([a, b] for a, b in combinations(options, 2) if a[1] != b[1]),
                   key=lambda pair: pair[0][0] + pair[1][0])
    for change in [[o] for o in options] + pairs:
        fixed = list(board)
        for _, i, digit in change:
            fixed[i] = digit
        solution = try_solve(fixed)
        if solution:
            return solution, fixed, {i: board[i] for _, i, _ in change}
    return None, board, {}


class SolutionCache:
    """Kamera modu: tahta önceki kareyle neredeyse aynıysa önceki çözümü kullanır, titremeyi önler."""

    def __init__(self):
        self.board = self.solution = None

    def lookup(self, board, scores):
        if self.board and sum(a == b for a, b in zip(board, self.board)) >= 78:
            return self.board, self.solution
        solution, board, _ = correct_and_solve(board, scores)
        if solution:
            self.board, self.solution = board, solution
            return board, solution
        return None


def draw_solution(frame, corners, board, solution):
    overlay = np.zeros((WARP, WARP), np.uint8)
    for i in range(81):
        if board[i] == 0:
            r, c = divmod(i, 9)
            text = str(solution[i])
            (tw, th), _ = cv2.getTextSize(text, FONT, 1.2, 3)
            cv2.putText(overlay, text, (c * CELL + (CELL - tw) // 2, r * CELL + (CELL + th) // 2),
                        FONT, 1.2, 255, 3, cv2.LINE_AA)
    M = cv2.getPerspectiveTransform(SQUARE, corners)
    h, w = frame.shape[:2]
    alpha = cv2.cvtColor(cv2.warpPerspective(overlay, M, (w, h)), cv2.COLOR_GRAY2BGR)
    green = np.full_like(frame, (0, 170, 0))
    frame[:] = cv2.add(cv2.multiply(frame, 255 - alpha, scale=1 / 255),
                       cv2.multiply(green, alpha, scale=1 / 255))


HAND_FONT = (Path(__file__).parent / "fonts" / "Caveat.ttf").read_bytes()  # el yazısı, SIL OFL; bir kez okunur
INK = np.float32([150, 60, 25]) / 255  # BGR: tükenmez kalem mavisi


def draw_handwritten(frame, corners, board, solution):
    """Çözümü kağıda kalemle yazılmış gibi çizer.

    - Rakamlar ızgaranın fotoğraftaki gerçek boyutunda çizilir; bulanık fotoğrafa keskin rakam yapışmaz.
    - Her rakam biraz farklı açı, boyut, konum ve kalem baskısıyla yazılır. Rastgelelik hücreye göre
      sabittir: aynı tahta hep aynı görünür.
    - Mürekkep kağıdın üstüne boyanmaz, kağıdı koyulaştırır (çarpma karışımı); gölge ve ışık korunur.
    """
    side = np.mean([np.linalg.norm(corners[i] - corners[(i + 1) % 4]) for i in range(4)])
    cell = int(np.clip(side, 270, 1350)) // 9
    size = cell * 9
    mask = np.zeros((size, size), np.uint8)
    for i in range(81):
        if board[i]:
            continue
        rng = np.random.default_rng(i)
        font = ImageFont.truetype(BytesIO(HAND_FONT), int(cell * rng.uniform(0.85, 0.98)))
        font.set_variation_by_axes([rng.uniform(450, 650)])  # kalem baskısı / çizgi kalınlığı
        glyph = Image.new("L", (cell * 2, cell * 2), 0)
        ImageDraw.Draw(glyph).text((cell, cell), str(solution[i]), fill=int(255 * rng.uniform(0.85, 1)),
                                   font=font, anchor="mm")
        tilt = cv2.getRotationMatrix2D((cell, cell), rng.uniform(-8, 8), 1)
        glyph = cv2.warpAffine(np.array(glyph), tilt, (cell * 2, cell * 2), flags=cv2.INTER_CUBIC)
        r, c = divmod(i, 9)
        x = int(c * cell + cell / 2 + rng.uniform(-0.06, 0.06) * cell) - cell
        y = int(r * cell + cell / 2 + rng.uniform(-0.06, 0.06) * cell) - cell
        # Hücrenin 2 katı büyüklükteki rakam kesitini tahtaya yerleştir (kenarlarda taşanı kırp)
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + 2 * cell, size), min(y + 2 * cell, size)
        np.maximum(mask[y0:y1, x0:x1], glyph[y0 - y:y1 - y, x0 - x:x1 - x], out=mask[y0:y1, x0:x1])
    mask = cv2.GaussianBlur(mask, (0, 0), max(0.5, cell / 70))  # mürekkebin kağıda hafif yayılması
    # Sadece ızgaranın kapladığı bölgede çalış: tüm fotoğrafta karıştırma gereksiz yere yavaş
    h, w = frame.shape[:2]
    bx, by, bw, bh = cv2.boundingRect(corners.astype(np.int32))
    x0, y0, x1, y1 = max(bx, 0), max(by, 0), min(bx + bw + 1, w), min(by + bh + 1, h)
    square = np.float32([[0, 0], [size, 0], [size, size], [0, size]])
    to_roi = cv2.getPerspectiveTransform(square, corners - np.float32([x0, y0]))
    alpha = cv2.warpPerspective(mask, to_roi, (x1 - x0, y1 - y0))[..., None].astype(np.float32) / 255
    roi = frame[y0:y1, x0:x1]
    roi[:] = (roi * (1 - alpha * (1 - INK))).astype(np.uint8)


def draw_outline(frame, corners, solved):
    color = (0, 200, 0) if solved else (0, 200, 255)  # yeşil: çözüldü, sarı: ızgara bulundu
    thickness = max(2, frame.shape[1] // 400)
    cv2.polylines(frame, [corners.astype(np.int32)], True, color, thickness)


MESSAGES = {
    "cozuldu": "Çözüldü.",
    "izgara_yok": "Sudoku ızgarası bulunamadı. Izgaranın tamamının kadrajda ve net olduğundan emin olun.",
    "cozulemedi": "Rakamların bir kısmı okunamadı, yanlış çözüm göstermemek için durdum. "
                  "Daha net ya da daha yakından çekilmiş bir fotoğraf deneyin.",
}


@dataclass
class Result:
    image: np.ndarray                              # çözüm çizilmiş görüntü
    status: str                                    # "cozuldu" | "izgara_yok" | "cozulemedi"
    board: list = None                             # okunan (gerekirse düzeltilmiş) rakamlar, boş = 0
    solution: list = None
    corrected: dict = field(default_factory=dict)  # {hücre: ilk okunan rakam}: kurallarla düzeltilenler
    unsure: list = field(default_factory=list)     # okunurken emin olunamayan hücreler
    corners: np.ndarray = None                     # ızgaranın köşeleri, doğru yöne çevrilmiş


def solve_image(img, clf, trace=None):
    """Tek bir görselin baştan sona işlenmesi.

    trace sözlüğü verilirse "Nasıl gördüm?" paneli için ara sonuçlar ona yazılır.
    """
    out = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners = find_grid(gray, trace)
    if corners is None:
        return Result(out, "izgara_yok")
    if trace is not None:
        trace["chosen"] = corners
    corners, board, scores = read_board_any_rotation(gray, corners, clf)
    if trace is not None:
        trace["warped"] = warp_grid(gray, corners)
        trace["scores"] = scores
        find_digits(trace["warped"], trace)  # seçilen yönün çizgisiz hali ve rakam kutuları
    solution, board, corrected = correct_and_solve(board, scores)
    unsure = [i for i in unsure_cells(scores) if i not in corrected]
    if solution is None:
        draw_outline(out, corners, solved=False)  # sarı çerçeve: ızgara bulundu ama okunamadı
        return Result(out, "cozulemedi", board, unsure=unsure, corners=corners)
    # Çerçeve çizilmez: kağıda kalemle yazılmış görünümü bozmasın
    draw_handwritten(out, corners, board, solution)
    return Result(out, "cozuldu", board, solution, corrected, unsure, corners)


def process_frame(frame, clf, cache):
    """Kamera modu: bir kareyi işler, önbellekle titremeyi önler."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners = find_grid(gray)
    if corners is None:
        return frame
    corners, board, scores = read_board_any_rotation(gray, corners, clf)
    found = cache.lookup(board, scores)
    draw_outline(frame, corners, found is not None)
    if found:
        draw_solution(frame, corners, *found)
    return frame
