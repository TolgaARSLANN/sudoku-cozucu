"""İnsan gibi çözen çözücü: ipuçları, teknikler ve zorluk derecesi."""
import pytest

from ipucu import BOXES, ROWS, UNITS, box_line, candidates, explain, hidden_pair, naked_subset, x_wing
from solver import solve

EASY = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
INKALA = "800000000003600000070090200050007000000045700000100030001000068008500010090000400"  # "en zor sudoku"


def board_of(text):
    return [int(c) for c in text]


@pytest.mark.parametrize("text, level", [(EASY, "Kolay"), (INKALA, "Şeytani")])
def test_hints_lead_to_the_solution(text, level):
    board = board_of(text)
    result = explain(board)
    assert result["zorluk"] == level
    solution, filled = solve(board), list(board)
    for hint in result["ipuclari"]:
        assert filled[hint["hucre"]] == 0  # her ipucu boş bir hücreye
        assert hint["rakam"] == solution[hint["hucre"]]  # ve doğru rakamı yerleştirir
        assert hint["aciklama"] and hint["vurgu"]
        filled[hint["hucre"]] = hint["rakam"]
    assert filled == solution


def test_single_techniques_are_really_valid():
    # Kolay bulmacada sadece tekler kullanılır; her birinin gerekçesini bağımsız olarak doğrula
    board = board_of(EASY)
    for hint in explain(board)["ipuclari"]:
        i, d = hint["hucre"], hint["rakam"]
        cands = candidates(board)
        if hint["teknik"] == "Tek aday":
            assert cands[i] == {d}
        else:
            assert hint["teknik"] == "Gizli tek"
            assert any(i in unit and [j for j in unit if d in cands[j]] == [i] for _, unit in UNITS)
        board[i] = d


def test_hint_is_labeled_with_its_hardest_technique():
    result = explain(board_of(INKALA))
    with_steps = [h for h in result["ipuclari"] if h["on_adimlar"]]
    assert with_steps  # bu bulmacada ileri teknik gerekiyor
    for hint in with_steps:
        names = [s["teknik"] for s in hint["on_adimlar"]]
        assert hint["teknik"] in names or hint["teknik"] == "Deneme yanılma"
        assert not any(s["aciklama"][0].islower() for s in hint["on_adimlar"])  # rakamla başlayabilir


def test_no_unique_solution_returns_none():
    board = board_of(EASY)
    for i in (0, 1, 4, 9, 12, 13):
        board[i] = 0
    assert explain(board) is None


# ---------- İleri teknikler: kurgulanmış aday durumlarında doğru elemeyi yapıyorlar mı? ----------

def full_candidates():
    return [set(range(1, 10)) for _ in range(81)]


def test_naked_pair():
    cands = full_candidates()
    cands[0], cands[1] = {1, 2}, {1, 2}  # 1. satırın ilk iki hücresine sadece 1 ve 2 sığıyor
    removals, text, _ = naked_subset([0] * 81, cands, 2)
    assert (2, 1) in removals and (8, 2) in removals  # satırın geri kalanından elenir
    assert all(i in ROWS[0] and i not in (0, 1) for i, _ in removals)
    assert "sadece 1, 2 sığıyor" in text


def test_hidden_pair():
    cands = full_candidates()
    for i in ROWS[0][2:]:
        cands[i] -= {1, 2}  # 1. satırda 1 ve 2 sadece ilk iki hücreye sığıyor
    removals, text, _ = hidden_pair([0] * 81, cands)
    assert sorted({i for i, _ in removals}) == [0, 1]
    assert {d for _, d in removals} == set(range(3, 10))  # o iki hücrenin diğer adayları elenir
    assert "1 ve 2 sadece" in text


def test_box_line_reduction():
    cands = full_candidates()
    for i in BOXES[0]:
        if i // 9 != 0:
            cands[i].discard(3)  # sol üst kutuda 3 sadece 1. satırda olabilir
    removals, _, _ = box_line([0] * 81, cands)
    assert sorted(removals) == [(i, 3) for i in range(3, 9)]  # 1. satırın diğer kutularından 3 elenir


def test_x_wing():
    cands = full_candidates()
    for row in (0, 4):
        for i in ROWS[row]:
            if i % 9 not in (1, 7):
                cands[i].discard(5)  # 1. ve 5. satırda 5 sadece 2. ve 8. sütunda olabilir
    removals, text, corners = x_wing([0] * 81, cands)
    assert sorted(corners) == [1, 7, 37, 43]
    assert all(d == 5 and i % 9 in (1, 7) and i // 9 not in (0, 4) for i, d in removals)
    assert len(removals) == 14  # iki sütunun diğer 7'şer hücresi
    assert "1. ve 5. satır içinde" in text
