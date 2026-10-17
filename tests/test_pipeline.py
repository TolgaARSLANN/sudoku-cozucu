"""Uçtan uca testler: görüntü → okunan tahta → çözüm."""
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from digits import DigitClassifier
from vision import load_image, solve_image

IMAGES = Path(__file__).parent / "images"
PUZZLE = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
SCREENSHOTS = {
    "ekran_1.jpg": "985401000000030000106000000000500000402009003090063400060010000000306005200080001",
    "ekran_2.jpg": "000000708000065000005308009006403510040000070032109800200504300000820000807000000",
}


@pytest.fixture(scope="module")
def clf():
    return DigitClassifier()


def grid_image(puzzle, font_path, cell=60):
    """Beyaz kağıt üzerine (10 px kenar boşluklu) sudoku çizer."""
    S = cell * 9
    img = Image.new("L", (S + 20, S + 20), 255)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, cell * 2 // 3)
    for i in range(10):
        w = 4 if i % 3 == 0 else 1
        d.line([(10, 10 + i * cell), (10 + S, 10 + i * cell)], fill=0, width=w)
        d.line([(10 + i * cell, 10), (10 + i * cell, 10 + S)], fill=0, width=w)
    for i, ch in enumerate(puzzle):
        if ch != "0":
            r, col = divmod(i, 9)
            d.text((10 + col * cell + cell // 2, 10 + r * cell + cell // 2), ch, fill=0, font=font,
                   anchor="mm")
    return cv2.cvtColor(np.array(img), cv2.COLOR_GRAY2BGR)


def synthetic_photo(puzzle, font_path, corners, seed):
    """Eğik çekilmiş, gölgeli ve gürültülü sahte bir sudoku fotoğrafı üretir."""
    S = 540
    paper = grid_image(puzzle, font_path)
    rng = np.random.default_rng(seed)
    bg = rng.integers(60, 120, (720, 1000, 3)).astype(np.uint8)
    src = np.float32([[0, 0], [S + 20, 0], [S + 20, S + 20], [0, S + 20]])
    M = cv2.getPerspectiveTransform(src, np.float32(corners))
    mask = cv2.warpPerspective(np.full((S + 20, S + 20), 255, np.uint8), M, (1000, 720)) > 0
    bg[mask] = cv2.warpPerspective(paper, M, (1000, 720))[mask]
    shade = np.linspace(0.75, 1.0, 1000)[None, :, None]
    photo = np.clip(bg * shade + rng.normal(0, 6, bg.shape), 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(photo, (3, 3), 0)


@pytest.mark.parametrize("font, corners", [
    ("arial.ttf", [[250, 80], [760, 120], [800, 640], [200, 600]]),
    ("times.ttf", [[300, 60], [720, 90], [780, 680], [230, 650]]),
    ("verdana.ttf", [[200, 150], [700, 60], [820, 560], [260, 690]]),
])
def test_synthetic_photo(clf, font, corners):
    photo = synthetic_photo(PUZZLE, rf"C:\Windows\Fonts\{font}", corners, seed=len(font))
    result = solve_image(photo, clf)
    assert "".join(map(str, result.board)) == PUZZLE
    assert result.status == "cozuldu"


@pytest.mark.parametrize("name", SCREENSHOTS)
def test_screenshot(clf, name):
    result = solve_image(load_image(str(IMAGES / name)), clf)
    assert "".join(map(str, result.board)) == SCREENSHOTS[name]
    assert result.status == "cozuldu"


def test_picks_puzzle_over_small_solution_grid(clf):
    # Gazetelerde bulmacanın yanında dünkü çözüm küçük bir ızgara olarak basılır
    solved = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    page = np.full((700, 1000, 3), 255, np.uint8)
    page[20:580, 20:580] = grid_image(PUZZLE, r"C:\Windows\Fonts\arial.ttf")
    page[400:680, 650:930] = grid_image(solved, r"C:\Windows\Fonts\arial.ttf", cell=29)[:280, :280]
    result = solve_image(page, clf)
    assert "".join(map(str, result.board)) == PUZZLE


def test_grid_with_broken_border(clf):
    # Bulanık fotoğraflarda ince çizgiler kesik kesik kalır; dış çerçeve kapalı bir dörtgen olmaz
    page = np.full((640, 640, 3), 255, np.uint8)
    page[40:600, 40:600] = grid_image(PUZZLE, r"C:\Windows\Fonts\arial.ttf")
    for t in (120, 260, 400, 520):  # dört kenarda da birer boşluk
        page[t:t + 6, 44:56] = 255
        page[t:t + 6, 584:596] = 255
        page[44:56, t:t + 6] = 255
        page[584:596, t:t + 6] = 255
    result = solve_image(page, clf)
    assert "".join(map(str, result.board)) == PUZZLE


def test_image_without_sudoku(clf):
    blank = np.full((480, 640, 3), 200, np.uint8)
    assert solve_image(blank, clf).status == "izgara_yok"
