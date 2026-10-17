"""Çözümün kağıda kalemle yazılmış gibi çizilmesi."""
import numpy as np

from vision import draw_handwritten

# 900x900 piksellik düz bir "kağıt" ve ızgaranın tamamı: hücre 100 px
PAPER = np.full((900, 900, 3), (190, 205, 215), np.uint8)  # hafif sarımsı kağıt (BGR)
CORNERS = np.float32([[0, 0], [900, 0], [900, 900], [0, 900]])
SOLUTION = [(i % 9) + 1 for i in range(81)]


def draw(board):
    frame = PAPER.copy()
    draw_handwritten(frame, CORNERS, board, SOLUTION)
    return frame


def test_ink_only_darkens_paper():
    out = draw([0] * 81)
    assert (out <= PAPER).all()  # mürekkep kağıdı koyulaştırır, asla parlatmaz
    assert (out < PAPER).any()


def test_writes_only_into_empty_cells():
    board = SOLUTION.copy()
    board[40] = 0  # sadece ortadaki hücre boş
    changed = np.argwhere((draw(board) != PAPER).any(axis=2))
    (top, left), (bottom, right) = changed.min(axis=0), changed.max(axis=0)
    assert 400 - 20 <= top and bottom <= 500 + 20  # rakam kendi hücresinde kalır (biraz taşma serbest)
    assert 400 - 20 <= left and right <= 500 + 20


def test_same_board_looks_the_same():
    assert np.array_equal(draw([0] * 81), draw([0] * 81))


def test_ink_is_blue():
    out = draw([0] * 81).astype(int)
    darkening = (PAPER.astype(int) - out).reshape(-1, 3).sum(axis=0)  # B, G, R kanallarında toplam koyulaşma
    assert darkening[2] > 2 * darkening[0]  # kırmızı, maviden çok daha fazla emilir: mavi mürekkep
