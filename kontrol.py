"""Kalemle doldurulmuş sudokuyu kontrol etme.

1. Fotoğraftaki her rakam için: basılı mı el yazısı mı, yazı tipi okuyucusu ne okuyor, el yazısı
   sinir ağı (el_yazisi.onnx) hangi rakama ne olasılık veriyor.
2. Bulmaca, en güvenilir rakamlardan başlanarak kurulur; tek çözüm bulununca durulur.
3. El yazısı her rakam çözümle karşılaştırılır. Ağ emin değilse "yanlış" değil "kontrol et" denir.

Model ve tür ayrımı ağırlıkları egit_el_yazisi.py ile üretilir.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from digits import normalize
from solver import solve, solve_unique
from vision import SQUARE, WARP, find_digits, find_grid, grid_cell_size, grid_overlay, read_board_any_rotation

HERE = Path(__file__).parent
MODEL_FILE = HERE / "el_yazisi.onnx"
TYPE_FILE = HERE / "el_yazisi_tur.json"
SIZE = 28
REFERENCE = 12     # fotoğrafta yazı tipine en çok benzeyen bu kadar rakam "basılı örnek" sayılır
SURE_RIGHT = 0.1   # ağ çözümdeki rakama en az bu olasılığı veriyorsa doğru yazılmış
SURE_WRONG = 0.98  # değilse ve okuduğu rakamdan bu kadar eminse yanlış; ikisi de değilse "kontrol et"


def center(crop):
    """0-1 değerli kesiti en uzun kenarı 20 px olacak şekilde 28x28'e ortalar (MNIST biçimi)."""
    h, w = crop.shape
    scale = 20 / max(h, w)
    crop = cv2.resize(crop, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
    out = np.zeros((SIZE, SIZE), np.float32)
    h, w = crop.shape
    out[(SIZE - h) // 2:(SIZE - h) // 2 + h, (SIZE - w) // 2:(SIZE - w) // 2 + w] = crop
    return out.ravel()


def ink_vector(gray_crop, mask):
    """El yazısı ağının girdisi: ikili maske değil gri mürekkep yoğunluğu.

    İkili maske ince el yazısını kalınlaştırıp delikleri doldurur (8 → 1 gibi). Gri kesitte de sadece
    rakamın kendi maskesinin çevresi tutulur; ızgara çizgisi parçaları ağa gitmez.
    """
    ink = 255 - gray_crop.astype(np.float32)
    support = cv2.dilate(mask, np.ones((3, 3), np.uint8)) > 0
    paper = np.percentile(ink, 30)
    ink = np.clip((ink - paper) / max(ink[support].max() - paper, 1), 0, 1) * support
    ys, xs = np.nonzero(ink > 0.35)
    if len(xs) == 0:
        return np.zeros(SIZE * SIZE, np.float32)
    return center(ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def thickness(mask):
    """Çizgi kalınlığı (px): uzaklık dönüşümünün ortancasının iki katı."""
    dist = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 3)
    return 2 * float(np.median(dist[dist > 0]))


def type_features(font_dist, heights, thick):
    """Basılı/el yazısı ayrımı için, aynı fotoğraftaki basılı rakamlara GÖRE özellikler.

    Mutlak değerler fotoğraftan fotoğrafa çok değişir (bulanıklık, yazı tipi); ama aynı sayfadaki
    basılı rakamlar birbirine benzer, el yazısı onlardan farklıdır.
    """
    ref = np.argsort(font_dist)[:REFERENCE]  # muhtemelen basılı olanlar
    d0, h0, t0 = np.median(font_dist[ref]), np.median(heights[ref]), np.median(thick[ref])
    return np.stack([font_dist, font_dist / d0, np.abs(heights / h0 - 1), np.abs(thick / t0 - 1)], 1)


class HandwritingReader:
    def __init__(self):
        # Dosya yolu yerine bayt: OpenCV Windows'ta Türkçe karakterli yolları açamıyor
        self.net = cv2.dnn.readNetFromONNX(np.fromfile(MODEL_FILE, np.uint8))
        t = json.loads(TYPE_FILE.read_text())
        self.mean, self.std, self.weights = (np.float32(t[k]) for k in ("ortalama", "sapma", "agirlik"))

    def probabilities(self, vecs):
        """(n, 784) → (n, 9): her rakam için 1-9 olasılıkları."""
        self.net.setInput(np.asarray(vecs, np.float32).reshape(-1, 1, SIZE, SIZE))
        logits = self.net.forward()
        e = np.exp(logits - logits.max(1, keepdims=True))
        return e / e.sum(1, keepdims=True)

    def hand_probability(self, features):
        """Lojistik regresyon: el yazısı olma olasılığı."""
        z = (features - self.mean) / self.std @ self.weights[:-1] + self.weights[-1]
        return 1 / (1 + np.exp(-z))


@dataclass
class Cell:
    hand: float          # el yazısı olma olasılığı
    printed: int         # yazı tipi okuyucusunun okuduğu rakam
    probs: np.ndarray    # el yazısı ağının 1-9 olasılıkları

    @property
    def is_hand(self):
        return self.hand >= 0.5

    @property
    def value(self):
        return int(self.probs.argmax()) + 1 if self.is_hand else self.printed


def extract(img, clf):
    """Fotoğraftaki rakamlar, sinir ağından bağımsız kısım (eğitim de bunu kullanır).

    Döner: köşeler (ızgara yoksa None), hücreler, ağ girdileri (n, 784), tür özellikleri (n, 4),
    yazı tipi okumaları (n,).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners = find_grid(gray)
    if corners is None:
        return None, [], None, None, None
    corners, _, _ = read_board_any_rotation(gray, corners, clf)
    warped = cv2.warpPerspective(gray, cv2.getPerspectiveTransform(corners, SQUARE), (WARP, WARP))
    trace = {}
    digits = find_digits(warped, trace)
    if not digits:
        return corners, [], None, None, None
    masks, boxes = list(digits.values()), trace["boxes"]
    font_dist = clf.class_distances([normalize(m) for m in masks])
    heights = np.float32([h for _, _, _, h in boxes])
    thick = np.float32([thickness(m) for m in masks])
    vecs = np.array([ink_vector(warped[y:y + h, x:x + w], m) for m, (x, y, w, h) in zip(masks, boxes)])
    features = type_features(font_dist.min(1), heights, thick)
    return corners, list(digits), vecs, features, font_dist.argmin(1) + 1


def read_cells(img, clf, reader):
    """Döner: (köşeler, {hücre: Cell}); ızgara yoksa (None, {})."""
    corners, idxs, vecs, features, printed = extract(img, clf)
    if not idxs:
        return corners, {}
    hand, probs = reader.hand_probability(features), reader.probabilities(vecs)
    return corners, {i: Cell(float(hand[k]), int(printed[k]), probs[k]) for k, i in enumerate(idxs)}


def trust(cell):
    """Rakamın bulmacaya ipucu olarak girme sırası, 0 en güvenilir."""
    if cell.printed == int(cell.probs.argmax()) + 1 and cell.probs.max() >= 0.5:
        return 0  # iki okuyucu aynı rakamı okuyor: basılı rakamları ikisi de tanır
    if not cell.is_hand or cell.probs.max() >= 0.9:
        return 1
    return 2      # el yazısı sanıldı ama ağ emin değil: el yazısı sanılan bulanık bir basılı rakam olabilir


def build_puzzle(cells):
    """Rakamları en güvenilirden başlayarak ipucu yapar; tek çözüm bulununca durur.

    Sıra: trust(), eşitlikte basılı olma ihtimali. Basılı sanılan el yazısında iki okuyucu genelde
    anlaşamaz; sona kalır ve bulmacayı bozmaz. Çelişki çıkaran rakam (yanlış yazılmış ya da yanlış
    okunmuş) ipucu yapılmaz.
    """
    board = [0] * 81
    for i in sorted(cells, key=lambda i: (trust(cells[i]), cells[i].hand)):
        trial = list(board)
        trial[i] = cells[i].value
        if solve(trial, max_steps=2000) is None:
            continue
        board = trial
        if sum(map(bool, board)) >= 17:
            solution = solve_unique(board)
            if solution:
                return solution
    return None


def verdict(cell, digit):
    """El yazısı bir rakam için: "dogru" | "yanlis" | "kontrol"."""
    if cell.probs[digit - 1] >= SURE_RIGHT:
        return "dogru"
    return "yanlis" if cell.probs.max() >= SURE_WRONG else "kontrol"


def judge(cells, solution):
    """{hücre: "basili"|"dogru"|"yanlis"|"kontrol"}.

    Basılı rakam çözümle çelişemez: çelişen "basılı" rakam büyük ihtimalle basılı sanılan bir el
    yazısıdır (yanlış yazılmış da olabilir); onu da el yazısı ağı değerlendirir.
    """
    return {i: verdict(c, solution[i]) if c.is_hand or c.printed != solution[i] else "basili"
            for i, c in cells.items()}


MARK_COLORS = {"yanlis": (40, 40, 210), "kontrol": (0, 140, 245)}  # BGR: kırmızı, turuncu


def draw_marks(frame, corners, verdicts):
    """Yanlış rakamların etrafına kırmızı, emin olunmayanlara turuncu kalem halkası çizer."""
    cell = grid_cell_size(corners)  # halka ızgaranın fotoğraftaki boyutunda çizilir
    size = cell * 9
    for kind, color in MARK_COLORS.items():
        mask = np.zeros((size, size), np.uint8)
        for i, v in verdicts.items():
            if v == kind:
                r, c = divmod(i, 9)
                center = (int((c + 0.5) * cell), int((r + 0.5) * cell))
                cv2.ellipse(mask, center, (int(cell * 0.44), int(cell * 0.4)), -8, 20, 375, 255,
                            max(2, cell // 14), cv2.LINE_AA)  # biraz eğik, ucu üst üste binen halka
        if mask.any():
            roi, alpha = grid_overlay(frame, corners, mask)
            roi[:] = (roi * (1 - alpha) + np.float32(color) * alpha).astype(np.uint8)


@dataclass
class CheckResult:
    image: np.ndarray                             # yanlışları işaretlenmiş görüntü
    status: str                                   # "kontrol_edildi" | "izgara_yok" | "cozulemedi"
    solution: list = None
    verdicts: dict = field(default_factory=dict)  # {hücre: "basili"|"dogru"|"yanlis"|"kontrol"}
    read: dict = field(default_factory=dict)      # {hücre: kağıtta okunan rakam}
    corners: np.ndarray = None


def check_image(img, clf, reader):
    out = img.copy()
    corners, cells = read_cells(img, clf, reader)
    if corners is None:
        return CheckResult(out, "izgara_yok")
    solution = build_puzzle(cells)
    if solution is None:
        return CheckResult(out, "cozulemedi", corners=corners)
    verdicts = judge(cells, solution)
    # Kağıtta ne yazıyor: basılı rakam yazı tipinden; el yazısı doğruysa çözümdeki rakam, değilse ağın okuduğu
    read = {i: c.printed if v == "basili" else solution[i] if v == "dogru" else int(c.probs.argmax()) + 1
            for (i, c), v in zip(cells.items(), verdicts.values())}
    draw_marks(out, corners, verdicts)
    return CheckResult(out, "kontrol_edildi", solution, verdicts, read, corners)
