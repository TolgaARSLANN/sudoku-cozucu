"""Komut satırı."""
import cv2

import cli
from digits import DigitClassifier
from test_pipeline import PUZZLE, grid_image
from vision import save_image


def test_quality_check_gets_image_and_corners_of_same_size(tmp_path, monkeypatch):
    # Büyük fotoğraf işlemden önce küçültülür; kalite kontrolü de küçültülmüş görselle çalışmalı,
    # yoksa köşeler görselin yanlış yerini gösterir
    puzzle = "".join("0" if i in (0, 1, 4, 9, 12, 13) else ch for i, ch in enumerate(PUZZLE))  # çözülemez
    big = cv2.resize(grid_image(puzzle, r"C:\Windows\Fonts\arial.ttf"), None, fx=5, fy=5)  # 2800 px
    path = tmp_path / "buyuk.jpg"
    save_image(str(path), big)
    seen = []
    monkeypatch.setattr(cli, "check_quality", lambda img, corners: seen.append((img.shape, corners)) or [])
    cli.solve_files([str(path)], DigitClassifier(), show_window=False)
    (h, w, _), corners = seen[0]
    assert max(h, w) == 1280
    assert corners.max() <= max(h, w)
