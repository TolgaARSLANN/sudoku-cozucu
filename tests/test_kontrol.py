"""Kalemle doldurulmuş sudoku kontrolü."""
from io import BytesIO

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from digits import DigitClassifier
from kontrol import Cell, HandwritingReader, build_puzzle, check_image, draw_marks, judge, verdict
from solver import solve
from test_pipeline import IMAGES, grid_image
from vision import HAND_FONT, load_image

PUZZLE = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
SOLUTION = solve([int(c) for c in PUZZLE])


def sure(digit, p=0.999):
    """El yazısı ağının digit'ten p kadar emin olduğu olasılıklar."""
    probs = np.full(9, (1 - p) / 8, np.float32)
    probs[digit - 1] = p
    return probs


def printed(digit):
    return Cell(hand=0.05, printed=digit, probs=sure(digit, 0.9))  # iki okuyucu da aynı rakamı okur


def handwritten(digit):
    return Cell(hand=0.95, printed=(digit % 9) + 1, probs=sure(digit))


def filled(mistakes=()):
    """Basılı ipuçları + boş hücrelerin hepsi el yazısıyla doldurulmuş tahta."""
    cells = {}
    for i, c in enumerate(PUZZLE):
        if c != "0":
            cells[i] = printed(int(c))
        else:
            cells[i] = handwritten(mistakes[i] if i in dict(mistakes) else SOLUTION[i])
    return cells


def test_verdict_rules():
    assert verdict(handwritten(4), 4) == "dogru"
    assert verdict(handwritten(4), 9) == "yanlis"                    # ağ 4 okuduğundan emin
    assert verdict(Cell(0.95, 1, sure(4, 0.7)), 9) == "kontrol"      # emin değil: "yanlış" deme
    probs = sure(4, 0.85)
    probs[8] = 0.12
    assert verdict(Cell(0.95, 1, probs), 9) == "dogru"               # çözümdeki rakam da makul olasılıkta


def test_solution_ignores_handwriting_mistakes():
    mistakes = {2: 1, 3: 2, 80: 5}  # çözümde 4, 6, 9
    assert build_puzzle(filled(mistakes)) == SOLUTION


def test_handwriting_taken_for_printed_does_not_break_puzzle():
    # El yazısı bir rakam yanlışlıkla basılı sanıldı ve yazı tipi okuyucusu onu yanlış okudu (1 → 7).
    # Bulmacaya ipucu olarak girerse çözümü bozar; iki okuyucu anlaşmadığı için sona bırakılmalı.
    cells = {i: c for i, c in filled().items() if PUZZLE[i] != "0"}
    i = PUZZLE.index("0")
    cells[i] = Cell(hand=0.03, printed=SOLUTION[i] % 9 + 1, probs=sure(SOLUTION[i]))
    assert build_puzzle(cells) == SOLUTION


def test_printed_taken_for_handwriting_with_unsure_network_does_not_break_puzzle():
    # Bulanık basılı bir rakam el yazısı sanıldı; ağ emin olmadan yanlış okudu (yazı tipi doğru okumuştu)
    cells = {i: c for i, c in filled().items() if PUZZLE[i] != "0"}
    i = PUZZLE.index("5")
    cells[i] = Cell(hand=0.6, printed=5, probs=sure(2, 0.3))
    assert build_puzzle(cells) == SOLUTION


def test_mistake_taken_for_printed_is_still_judged():
    # Yanlış yazılmış el yazısı rakam basılı sanıldı: basılı rakam çözümle çelişemeyeceği için yine değerlendirilir
    i = PUZZLE.index("0")
    wrong = SOLUTION[i] % 9 + 1
    cells = {i: Cell(hand=0.2, printed=wrong, probs=sure(wrong)), 0: printed(5)}
    assert judge(cells, SOLUTION) == {i: "yanlis", 0: "basili"}


def test_marks_only_flagged_cells():
    paper = np.full((900, 900, 3), 230, np.uint8)  # hücre 100 px
    frame = paper.copy()
    draw_marks(frame, np.float32([[0, 0], [900, 0], [900, 900], [0, 900]]), {40: "yanlis", 0: "kontrol", 1: "dogru"})
    changed = (frame != paper).any(axis=2)
    assert changed[400:500, 400:500].any() and changed[0:100, 0:100].any()
    assert not changed[0:100, 100:200].any()  # doğru hücreye dokunulmaz
    assert changed.sum() == changed[400:500, 400:500].sum() + changed[0:100, 0:100].sum()  # halka hücrede kalır
    darkening = (paper[400:500, 400:500].astype(int) - frame[400:500, 400:500]).reshape(-1, 3).sum(axis=0)
    assert darkening[0] > 5 * darkening[2]  # BGR: mavi ve yeşil azalır, kırmızı kalır


def test_unsolvable_returns_none():
    cells = {i: printed(int(c)) for i, c in enumerate(PUZZLE[:30]) if c != "0"}  # 17'den az ipucu
    assert build_puzzle(cells) is None


def pen_filled_page(written, cell=60):
    """Arial ile basılmış bulmaca; boş hücrelere el yazısı yazı tipiyle, kalem renginde rakamlar."""
    page = Image.fromarray(cv2.cvtColor(grid_image(PUZZLE, r"C:\Windows\Fonts\arial.ttf", cell), cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(page)
    for i, digit in written.items():
        rng = np.random.default_rng(i)
        font = ImageFont.truetype(BytesIO(HAND_FONT), int(cell * rng.uniform(0.75, 0.9)))
        r, c = divmod(i, 9)
        draw.text((10 + c * cell + cell // 2, 10 + r * cell + cell // 2), str(digit), fill=(40, 50, 120),
                  font=font, anchor="mm")
    return cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)


@pytest.fixture(scope="module")
def models():
    return DigitClassifier(), HandwritingReader()


def test_check_pen_filled_page(models):
    empty = [i for i, c in enumerate(PUZZLE) if c == "0"]
    written = {i: SOLUTION[i] for i in empty[:40]}  # 40 hücre dolduruldu, gerisi boş
    wrong_cell = empty[5]
    written[wrong_cell] = SOLUTION[wrong_cell] % 9 + 1
    result = check_image(pen_filled_page(written), *models)
    assert result.status == "kontrol_edildi"
    assert result.solution == SOLUTION
    assert result.verdicts[wrong_cell] == "yanlis"
    assert result.read[wrong_cell] == written[wrong_cell]
    assert all(result.verdicts[i] == "basili" for i, c in enumerate(PUZZLE) if c != "0")
    # Düzgün bir yazı tipi basılıya benzer; bir kısmı "basılı" sayılabilir ama doğruya "yanlış" denmez
    assert all(result.verdicts[i] in ("dogru", "basili") for i in written if i != wrong_cell)
    assert set(result.verdicts) <= set(written) | {i for i, c in enumerate(PUZZLE) if c != "0"}  # boşlar boş


def test_check_real_pen_photo(models):
    # Telefonla çekilmiş, mavi tükenmez kalemle doldurulmuş gazete bulmacası (wichtounet/sudoku_dataset, CC-BY-4.0)
    written = [int(c) for c in "825341769371569482469728513698154237243876951517932648934687125786215394152493876"]
    result = check_image(load_image(str(IMAGES / "kalem.jpg")), *models)
    assert result.solution == written  # tamamen ve doğru doldurulmuş
    assert "yanlis" not in result.verdicts.values()
    assert sum(v == "dogru" for v in result.verdicts.values()) >= 45
