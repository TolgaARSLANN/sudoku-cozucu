"""Fotoğraf kalite uyarıları: her sorun yapay olarak üretilip doğru uyarının çıktığı denenir."""
from pathlib import Path

import cv2
import numpy as np

from kalite import check_quality
from test_pipeline import PUZZLE, grid_image
from vision import find_grid, load_image

FONT = r"C:\Windows\Fonts\arial.ttf"
# Fotoğrafa benzesin diye: gri arka plan üzerinde, kağıdı hafif gri (ekran görüntüsü kadar beyaz değil)
CORNERS = np.float32([[100, 100], [660, 100], [660, 660], [100, 660]])


def photo(paper_gray=200):
    canvas = np.full((760, 760, 3), 90, np.uint8)
    sheet = grid_image(PUZZLE, FONT).astype(np.float32) * (paper_gray / 255)
    canvas[100:660, 100:660] = sheet.astype(np.uint8)
    return canvas


def test_good_photo_has_no_warnings():
    assert check_quality(photo(), CORNERS) == []


def test_screenshot_is_not_glare():
    # Ekran görüntüsünün zemini bembeyaz; bu parlama sayılmamalı
    img = load_image(str(Path(__file__).parent / "images" / "ekran_1.jpg"))
    assert check_quality(img, find_grid(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))) == []


def test_blurry():
    assert "bulanik" in check_quality(cv2.GaussianBlur(photo(), (0, 0), 6), CORNERS)


def test_small_grid():
    small = cv2.resize(photo(), None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA)
    assert "kucuk" in check_quality(small, CORNERS * 0.3)


def test_dark():
    assert "karanlik" in check_quality((photo() * 0.3).astype(np.uint8), CORNERS)


def test_glare():
    img = photo()
    cv2.circle(img, (380, 380), 80, (255, 255, 255), -1)  # ızgaranın ortasında patlamış beyaz leke
    assert "parlama" in check_quality(img, CORNERS)


def test_no_grid_checks_whole_image():
    blurry = cv2.GaussianBlur(photo(), (0, 0), 6)
    assert "bulanik" in check_quality(blurry)
