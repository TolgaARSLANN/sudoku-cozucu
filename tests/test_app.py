import io
from pathlib import Path

import pytest

import app as server
from app import app

IMAGES = Path(__file__).parent / "images"


@pytest.fixture
def client():
    return app.test_client()


def post(client, data, name="foto.jpg"):
    return client.post("/api/coz", data={"gorsel": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Sudoku Çözücü" in res.get_data(as_text=True)


def test_solves_uploaded_screenshot(client):
    res = post(client, (IMAGES / "ekran_1.jpg").read_bytes())
    data = res.get_json()
    assert res.status_code == 200
    assert data["durum"] == "cozuldu"
    assert len(data["cozum"]) == 81 and all(data["cozum"])
    assert data["gorsel"].startswith("data:image/jpeg;base64,")
    assert data["duzeltilen"] == [] and isinstance(data["emin_degil"], list)


def test_rejects_non_image(client):
    res = post(client, b"bu bir resim degil", "not.txt")
    assert res.status_code == 400
    assert "hata" in res.get_json()


PUZZLE = [int(c) for c in
          "530070000600195000098000060800060003400803001700020006060000280000419005000080079"]


def test_solve_corrected_board(client):
    data = client.post("/api/coz-tahta", json={"tahta": PUZZLE}).get_json()
    assert data["durum"] == "cozuldu" and all(data["cozum"])


def test_corrected_board_with_missing_digits(client):
    board = PUZZLE.copy()
    for i in (0, 1, 4, 9, 12, 13):
        board[i] = 0
    data = client.post("/api/coz-tahta", json={"tahta": board}).get_json()
    assert data["durum"] == "cozulemedi" and "birden fazla" in data["mesaj"]


def test_corrected_board_with_conflict(client):
    board = PUZZLE.copy()
    board[2] = 5
    data = client.post("/api/coz-tahta", json={"tahta": board}).get_json()
    assert data["durum"] == "cozulemedi" and "çelişki" in data["mesaj"]


def test_invalid_board(client):
    assert client.post("/api/coz-tahta", json={"tahta": [1, 2, 3]}).status_code == 400


def test_rejects_too_many_pixels(client, monkeypatch):
    # Sınırı küçültüp normal bir görselle denenir; gerçek 50 MP'lik görsel üretmek testi yavaşlatırdı
    monkeypatch.setattr(server, "MAX_PIXELS", 1000)
    res = post(client, (IMAGES / "ekran_1.jpg").read_bytes())
    assert res.status_code == 413
    assert "çözünürlüğü çok yüksek" in res.get_json()["hata"]


def test_missing_file(client):
    res = client.post("/api/coz")
    assert res.status_code == 400
