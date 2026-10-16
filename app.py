"""Sudoku Çözücü - web arayüzü.

    python app.py      →  http://127.0.0.1:5000
"""
import base64
from io import BytesIO

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image

from digits import DigitClassifier
from solver import solve, solve_unique
from vision import MESSAGES, solve_image

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
clf = DigitClassifier()
MAX_PIXELS = 50_000_000  # ~50 megapiksel: güncel telefon fotoğrafları sığar


def too_many_pixels(data):
    """Görseli açmadan, sadece dosya başlığından boyutuna bakar.

    Dosya boyutu sınırı yetmez: tek renkli bir PNG birkaç yüz KB olup açılınca belleği doldurabilir.
    """
    try:
        with Image.open(BytesIO(data)) as im:
            width, height = im.size
    except Image.DecompressionBombError:
        return True
    except OSError:
        return False  # görsel değilse aşağıdaki çözümleme zaten reddeder
    return width * height > MAX_PIXELS


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/coz")
def solve_upload():
    file = request.files.get("gorsel")
    if file is None:
        return jsonify(hata="Görsel gönderilmedi."), 400
    data = file.read()
    if too_many_pixels(data):
        return jsonify(hata=f"Görselin çözünürlüğü çok yüksek (en fazla {MAX_PIXELS // 1_000_000} megapiksel). "
                            "Daha küçük bir görsel dene."), 413
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify(hata="Bu dosya görsel olarak okunamadı. JPG ya da PNG deneyin."), 400

    result = solve_image(img, clf)
    out = result.image
    scale = min(1.0, 1600 / max(out.shape[:2]))  # telefon fotoğraflarını tarayıcı için küçült
    if scale < 1:
        out = cv2.resize(out, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 90])
    message = MESSAGES[result.status]
    if result.corrected:
        message += (f" {len(result.corrected)} rakamı okurken emin olamadım, sudoku kurallarına göre"
                    " düzelttim (turuncu olanlar).")
    return jsonify(
        durum=result.status,
        mesaj=message,
        tahta=result.board,
        cozum=result.solution,
        duzeltilen=[{"hucre": i, "okunan": old} for i, old in result.corrected.items()],
        emin_degil=result.unsure,
        gorsel="data:image/jpeg;base64," + base64.b64encode(buf).decode(),
    )


@app.post("/api/coz-tahta")
def solve_board():
    """Kullanıcının düzelttiği tahtayı çözer (fotoğrafta okunamayan rakamlar için)."""
    board = (request.get_json(silent=True) or {}).get("tahta")
    if not (isinstance(board, list) and len(board) == 81
            and all(isinstance(v, int) and 0 <= v <= 9 for v in board)):
        return jsonify(hata="Geçersiz tahta."), 400
    solution = solve_unique(board)
    if solution:
        return jsonify(durum="cozuldu", mesaj="Çözüldü.", cozum=solution)
    if solve(board):
        message = "Bu tahtanın birden fazla çözümü var; eksik rakam olabilir."
    else:
        message = "Bu tahtada çelişki var ya da çözümü yok. Rakamları kontrol et."
    return jsonify(durum="cozulemedi", mesaj=message, cozum=None)


@app.errorhandler(413)
def too_large(_):
    return jsonify(hata="Dosya çok büyük (en fazla 20 MB)."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
