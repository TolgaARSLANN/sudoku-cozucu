"""Sudoku kurallarıyla okuma hatası düzeltme."""
import numpy as np

from vision import correct_and_solve, unsure_cells

PUZZLE = [int(c) for c in
          "530070000600195000098000060800060003400803001700020006060000280000419005000080079"]
SOLUTION = [int(c) for c in
            "534678912672195348198342567859761423426853791713924856961537284287419635345286179"]


def scores_for(board, overrides=None):
    """Her rakam için uzaklıklar: okunan rakam 1.0, diğerleri 3.0; overrides ile özelleştirilir."""
    scores = {}
    for i, v in enumerate(board):
        if v:
            d = np.full(9, 3.0)
            d[v - 1] = 1.0
            scores[i] = d
    for i, (first, second, margin) in (overrides or {}).items():
        d = np.full(9, 3.0)
        d[first - 1] = 1.0
        d[second - 1] = 1.0 + margin
        scores[i] = d
    return scores


def misread(index, as_digit):
    board = PUZZLE.copy()
    board[index] = as_digit
    return board


def test_correct_board_needs_no_correction():
    solution, board, corrected = correct_and_solve(PUZZLE, scores_for(PUZZLE))
    assert solution == SOLUTION and corrected == {}


def test_unsure_misread_is_corrected():
    # 4. hücredeki 7, emin olunmadan 1 okunmuş; 2. tahmin 7
    board = misread(4, 1)
    solution, fixed, corrected = correct_and_solve(board, scores_for(board, {4: (1, 7, 0.2)}))
    assert solution == SOLUTION
    assert fixed[4] == 7 and corrected == {4: 1}


def test_confident_misread_is_not_touched():
    # Aynı hata ama sınıflandırıcı çok emin: kendi kafasına göre değiştirmemeli
    board = misread(4, 1)
    solution, _, corrected = correct_and_solve(board, scores_for(board, {4: (1, 7, 2.0)}))
    assert solution is None and corrected == {}


def test_unsure_cells():
    scores = scores_for(PUZZLE, {0: (5, 6, 0.1), 1: (3, 8, 1.5)})
    assert unsure_cells(scores) == [0]
