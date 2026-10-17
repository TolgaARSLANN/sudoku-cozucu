"""Gizlilik: yüklenen görsel hiçbir zaman diske yazılmaz, sadece bellekte işlenir.

İki yoldan izlenir:
- Python denetim kancası (audit hook): Python üzerinden yapılan her yazma amaçlı dosya açma, geçici dosya
  ve klasör oluşturma, taşıma, silme yakalanır.
- Proje klasörünün öncesi/sonrası karşılaştırması: OpenCV gibi C kodunun yazdıkları da görülür.
"""
import io
import json
import os
import sys
from pathlib import Path

import cv2
import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.test import encode_multipart

from app import app
from vision import load_image

ROOT = Path(__file__).parent.parent
IMAGES = Path(__file__).parent / "images"
WRITE_EVENTS = {"tempfile.mkstemp", "tempfile.mkdtemp", "os.mkdir", "os.rename", "os.replace", "os.remove",
                "os.truncate", "shutil.copyfile", "shutil.move"}
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC

_recording = None  # kayıt sürerken yakalanan yazma işlemleri


def _hook(event, args):
    if _recording is None:
        return
    if event == "open":
        path, mode, flags = args
        writes = any(c in mode for c in "wax+") if isinstance(mode, str) else bool((flags or 0) & WRITE_FLAGS)
        if writes:
            _recording.append((event, path))
    elif event in WRITE_EVENTS:
        _recording.append((event, args))


sys.addaudithook(_hook)  # kanca kaldırılamaz; kayıt dışında hiçbir şey yapmaz


def snapshot():
    return {p: p.stat().st_mtime_ns for p in ROOT.rglob("*")
            if p.is_file() and not ({".git", "node_modules", "veri", "__pycache__"} & set(p.parts))}


@pytest.fixture
def disk_writes():
    global _recording
    before = snapshot()
    _recording = []
    yield _recording
    _recording = None
    after = snapshot()
    changed = [p for p in after if before.get(p) != after[p]]
    assert changed == [], f"Proje klasöründe değişen dosyalar: {changed}"


def big_photo():
    """Telefon fotoğrafı boyutunda (500 KB'tan büyük) bir görsel."""
    img = load_image(str(IMAGES / "ekran_1.jpg"))
    data = cv2.imencode(".png", cv2.resize(img, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC))[1].tobytes()
    assert len(data) > 500 * 1024
    return data


def post(client, url, fields):
    """İstek gövdesi bellekte hazırlanır: test istemcisi büyük istekleri kendisi geçici dosyaya yazıyor
    (sunucuyla ilgisi yok, ölçümü karıştırmasın)."""
    fields = {k: FileStorage(io.BytesIO(v[0]), v[1]) if isinstance(v, tuple) else v for k, v in fields.items()}
    boundary, body = encode_multipart(fields)
    return client.post(url, data=body, content_type=f"multipart/form-data; boundary={boundary}")


def test_no_disk_writes_while_processing_uploads(disk_writes):
    client = app.test_client()
    data = big_photo()
    res = post(client, "/api/coz", {"gorsel": (data, "foto.png")}).get_json()
    assert res["durum"] == "cozuldu"
    post(client, "/api/coz-tahta", {"tahta": json.dumps(res["tahta"]), "koseler": json.dumps(res["koseler"]),
                                    "gorsel": (data, "foto.png")})
    assert post(client, "/api/kontrol", {"gorsel": (data, "foto.png")}).status_code == 200
    assert post(client, "/api/kontrol", {"gorsel": ((IMAGES / "kalem.jpg").read_bytes(), "k.jpg")}
                ).get_json()["durum"] == "kontrol_edildi"
    assert disk_writes == [], f"Diske yazma girişimi: {disk_writes}"


def test_hook_catches_temporary_files(disk_writes):
    # Kancanın gerçekten çalıştığının kanıtı: bilerek geçici dosya oluşturulur
    import tempfile
    with tempfile.TemporaryFile() as f:
        f.write(b"x")
    assert disk_writes, "denetim kancası geçici dosyayı yakalamadı"
    disk_writes.clear()
