import base64
import io
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import app as server
from app import app
from vision import load_image

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
    assert data["uyarilar"] == []  # çözüldüyse kalite uyarısı yok
    assert data["zorluk"] in ("Kolay", "Orta", "Zor", "Şeytani")
    assert len(data["ipuclari"]) == data["tahta"].count(0)  # her boş hücre için bir ipucu


def test_returns_processing_steps(client):
    steps = post(client, (IMAGES / "ekran_1.jpg").read_bytes()).get_json()["adimlar"]
    assert len(steps) == 5
    assert all(s["baslik"] and s["aciklama"] and s["gorsel"].startswith("data:image/jpeg") for s in steps)


def test_steps_without_grid(client):
    _, png = cv2.imencode(".png", np.full((480, 640, 3), 200, np.uint8))
    data = post(client, png.tobytes(), "bos.png").get_json()
    assert data["durum"] == "izgara_yok"
    assert [s["baslik"] for s in data["adimlar"]] == ["Siyah-beyaz görüntü", "Izgara adayları"]


def test_quality_warnings_when_unreadable(client):
    # Bulanıklaştırılmış ekran görüntüsü: okunamaz, sebebi söylenmeli
    img = load_image(str(IMAGES / "ekran_1.jpg"))  # cv2.imread Türkçe karakterli yolu okuyamaz
    _, jpg = cv2.imencode(".jpg", cv2.GaussianBlur(img, (0, 0), 8))
    data = post(client, jpg.tobytes()).get_json()
    assert data["durum"] != "cozuldu"
    assert any("bulanık" in w for w in data["uyarilar"])


def test_rejects_non_image(client):
    res = post(client, b"bu bir resim degil", "not.txt")
    assert res.status_code == 400
    assert "hata" in res.get_json()


PUZZLE = [int(c) for c in
          "530070000600195000098000060800060003400803001700020006060000280000419005000080079"]


def post_board(client, board, image=None, corners=None):
    """Düzeltilmiş tahtayı gönderir; fotoğraf ve köşeler verilirse çözüm fotoğrafa çizilir."""
    data = {"tahta": json.dumps(board)}
    if image is not None:
        data["gorsel"] = (io.BytesIO(image), "foto.jpg")
        data["koseler"] = json.dumps(corners)
    return client.post("/api/coz-tahta", data=data, content_type="multipart/form-data")


def test_solve_corrected_board(client):
    data = post_board(client, PUZZLE).get_json()
    assert data["durum"] == "cozuldu" and all(data["cozum"])
    assert data["gorsel"] is None  # fotoğraf gönderilmediyse çizilecek bir şey yok
    assert data["zorluk"] == "Kolay" and len(data["ipuclari"]) == PUZZLE.count(0)


def test_corrected_board_with_missing_digits(client):
    board = PUZZLE.copy()
    for i in (0, 1, 4, 9, 12, 13):
        board[i] = 0
    data = post_board(client, board).get_json()
    assert data["durum"] == "cozulemedi" and "birden fazla" in data["mesaj"]


def test_corrected_board_with_conflict(client):
    board = PUZZLE.copy()
    board[2] = 5
    data = post_board(client, board).get_json()
    assert data["durum"] == "cozulemedi" and "çelişki" in data["mesaj"]


def test_invalid_board(client):
    assert post_board(client, [1, 2, 3]).status_code == 400


def test_draws_solution_on_photo_after_fix(client):
    # Aynı tahta ve köşeler geri gönderilince, ilk çözümdeki görselin aynısı çizilmeli
    photo = (IMAGES / "ekran_1.jpg").read_bytes()
    first = post(client, photo).get_json()
    fixed = post_board(client, first["tahta"], photo, first["koseler"]).get_json()
    assert fixed["durum"] == "cozuldu"
    assert fixed["gorsel"] == first["gorsel"]


def test_rejects_invalid_corners(client):
    photo = (IMAGES / "ekran_1.jpg").read_bytes()
    assert post_board(client, PUZZLE, photo, [[1, 2]]).status_code == 400


def test_rejects_too_many_pixels(client, monkeypatch):
    # Sınırı küçültüp normal bir görselle denenir; gerçek 50 MP'lik görsel üretmek testi yavaşlatırdı
    monkeypatch.setattr(server, "MAX_PIXELS", 1000)
    res = post(client, (IMAGES / "ekran_1.jpg").read_bytes())
    assert res.status_code == 413
    assert "çözünürlüğü çok yüksek" in res.get_json()["hata"]


def test_missing_file(client):
    res = client.post("/api/coz")
    assert res.status_code == 400


def check(client, data, name="foto.jpg"):
    return client.post("/api/kontrol", data={"gorsel": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_checks_pen_filled_photo(client):
    data = check(client, (IMAGES / "kalem.jpg").read_bytes()).get_json()
    assert data["durum"] == "kontrol_edildi"
    assert len(data["cozum"]) == 81 and all(data["cozum"])
    summary = data["ozet"]
    assert summary["yanlis"] == 0
    assert summary["dogru"] + summary["kontrol"] + summary["bos"] + \
        sum(r["durum"] == "basili" for r in data["sonuclar"]) == 81
    assert data["mesaj"].startswith(f"{summary['dogru']} doğru, 0 yanlış")
    assert all(r["durum"] in ("basili", "dogru", "yanlis", "kontrol") and 1 <= r["okunan"] <= 9
               for r in data["sonuclar"])
    assert data["gorsel"].startswith("data:image/jpeg;base64,")


def test_check_without_grid(client):
    _, png = cv2.imencode(".png", np.full((480, 640, 3), 200, np.uint8))
    data = check(client, png.tobytes(), "bos.png").get_json()
    assert data["durum"] == "izgara_yok" and data["cozum"] is None and data["sonuclar"] == []


def test_check_requires_image(client):
    assert client.post("/api/kontrol").status_code == 400


def test_large_photo_is_shrunk_consistently(client):
    # Büyük görseller işlemden önce en uzun kenarı 1280 px olacak şekilde küçültülür
    def enlarged(name, factor):
        img = load_image(str(IMAGES / name))
        return cv2.imencode(".jpg", cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC))[1].tobytes()

    data = enlarged("ekran_1.jpg", 10)  # 3600x3600
    res = post(client, data).get_json()
    assert res["durum"] == "cozuldu"
    assert np.float32(res["koseler"]).max() <= 1280  # köşeler küçültülmüş görsele göre
    shown = cv2.imdecode(np.frombuffer(base64.b64decode(res["gorsel"].split(",")[1]), np.uint8), cv2.IMREAD_COLOR)
    assert max(shown.shape[:2]) == 1280
    # Düzeltme sonrası çizim: aynı büyük dosya ve dönen köşelerle tutarlı çalışmalı
    drawn = client.post("/api/coz-tahta", data={"tahta": json.dumps(res["tahta"]), "koseler": json.dumps(res["koseler"]),
                                               "gorsel": (io.BytesIO(data), "foto.jpg")},
                        content_type="multipart/form-data").get_json()
    assert drawn["durum"] == "cozuldu" and drawn["gorsel"]
    assert check(client, enlarged("kalem.jpg", 3)).get_json()["durum"] == "kontrol_edildi"  # 3840x2880


def test_unexpected_error_is_turkish_json_and_logs_no_image(client, monkeypatch, caplog):
    def broken(*_):
        raise RuntimeError("deneme hatası")
    monkeypatch.setattr(server, "solve_image", broken)
    data = (IMAGES / "ekran_1.jpg").read_bytes()
    res = post(client, data)
    assert res.status_code == 500
    assert res.get_json()["hata"].startswith("Beklenmeyen bir hata oluştu")
    log = caplog.text
    assert "deneme hatası" in log and "/api/coz" in log  # ayrıntı sunucu kaydında
    assert base64.b64encode(data[:30]).decode()[:20] not in log and "JFIF" not in log  # görsel kayda girmez


def test_known_http_errors_keep_their_answers(client):
    assert client.get("/yok").status_code == 404
    assert client.post("/api/coz").status_code == 400
