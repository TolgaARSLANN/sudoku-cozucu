"""Sudoku Çözücü - web arayüzü.

    python app.py      →  http://127.0.0.1:5000
"""
import base64
import json
from io import BytesIO

import cv2
import numpy as np
from flask import Flask, Request, jsonify, request, send_from_directory
from PIL import Image
from werkzeug.exceptions import HTTPException

from adimlar import build_steps
from digits import DigitClassifier
from ipucu import explain
from kalite import WARNINGS, check_quality
from kontrol import HandwritingReader, check_image
from solver import solve, solve_unique
from vision import MESSAGES, draw_handwritten, limit_size, solve_image


class MemoryRequest(Request):
    """Yüklenen görsel hiçbir zaman diske yazılmaz.

    Werkzeug 500 KB'tan büyük yüklemeleri geçici dosyaya aktarır; telefon fotoğrafları hep daha büyük.
    Yükleme en fazla 20 MB (MAX_CONTENT_LENGTH) olduğu için bellekte tutmak güvenli.
    """

    def _get_file_stream(self, *args, **kwargs):
        return BytesIO()


app = Flask(__name__, static_folder="static")
app.request_class = MemoryRequest
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
clf = DigitClassifier()
reader = HandwritingReader()
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


def read_upload():
    """İstekteki görseli açar. Döner: (görsel, None) ya da (None, hata cevabı)."""
    file = request.files.get("gorsel")
    if file is None:
        return None, (jsonify(hata="Görsel gönderilmedi."), 400)
    data = file.read()
    if too_many_pixels(data):
        return None, (jsonify(hata=f"Görselin çözünürlüğü çok yüksek (en fazla {MAX_PIXELS // 1_000_000} "
                                   "megapiksel). Daha küçük bir görsel dene."), 413)
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None, (jsonify(hata="Bu dosya görsel olarak okunamadı. JPG ya da PNG deneyin."), 400)
    # Düzeltme sonrası çizimde de aynı küçültme: istemcinin geri gönderdiği köşeler bu boyuta göre
    return limit_size(img), None


def encode_image(img):
    """Görseli tarayıcı için küçültüp JPEG data URL'ine çevirir."""
    scale = min(1.0, 1600 / max(img.shape[:2]))  # telefon fotoğrafları gereğinden büyük
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def parse_corners(text):
    """İstemcinin geri gönderdiği 4 köşe noktası; geçersizse None."""
    try:
        corners = np.float32(json.loads(text))
    except (TypeError, ValueError):
        return None
    return corners if corners.shape == (4, 2) and np.isfinite(corners).all() else None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/coz")
def solve_upload():
    img, error = read_upload()
    if error:
        return error
    trace = {}  # "Nasıl gördüm?" paneli için ara sonuçlar
    result = solve_image(img, clf, trace)
    message = MESSAGES[result.status]
    if result.corrected:
        message += (f" {len(result.corrected)} rakamı okurken emin olamadım, sudoku kurallarına göre"
                    " düzelttim (turuncu olanlar).")
    # Kalite uyarıları sadece başarısızlıkta: eski telefonların çözülen fotoğrafları da "bulanık" ölçülüyor
    warnings = [] if result.status == "cozuldu" else check_quality(img, result.corners)
    analysis = explain(result.board) if result.solution else None
    return jsonify(
        durum=result.status,
        mesaj=message,
        tahta=result.board,
        cozum=result.solution,
        duzeltilen=[{"hucre": i, "okunan": old} for i, old in result.corrected.items()],
        emin_degil=result.unsure,
        uyarilar=[WARNINGS[w] for w in warnings],
        zorluk=analysis and analysis["zorluk"],
        ipuclari=analysis["ipuclari"] if analysis else [],
        koseler=None if result.corners is None else result.corners.tolist(),
        gorsel=encode_image(result.image),
        adimlar=[{"baslik": title, "aciklama": text, "gorsel": encode_image(image)}
                 for title, text, image in build_steps(img, trace, result)],
    )


@app.post("/api/coz-tahta")
def solve_board():
    """Kullanıcının düzelttiği tahtayı çözer (fotoğrafta okunamayan rakamlar için).

    Fotoğraf ve ızgara köşeleri de gönderilirse çözüm fotoğrafın üstüne çizilir.
    """
    try:
        board = json.loads(request.form.get("tahta", ""))
    except ValueError:
        board = None
    if not (isinstance(board, list) and len(board) == 81
            and all(isinstance(v, int) and 0 <= v <= 9 for v in board)):
        return jsonify(hata="Geçersiz tahta."), 400
    solution = solve_unique(board)
    if not solution:
        if solve(board):
            message = "Bu tahtanın birden fazla çözümü var; eksik rakam olabilir."
        else:
            message = "Bu tahtada çelişki var ya da çözümü yok. Rakamları kontrol et."
        return jsonify(durum="cozulemedi", mesaj=message, cozum=None, gorsel=None, zorluk=None, ipuclari=[])

    image = None
    if "gorsel" in request.files:
        img, error = read_upload()
        if error:
            return error
        corners = parse_corners(request.form.get("koseler"))
        if corners is None:
            return jsonify(hata="Izgaranın köşe bilgisi geçersiz."), 400
        draw_handwritten(img, corners, board, solution)
        image = encode_image(img)
    analysis = explain(board)
    return jsonify(durum="cozuldu", mesaj="Çözüldü.", cozum=solution, gorsel=image,
                   zorluk=analysis["zorluk"], ipuclari=analysis["ipuclari"])


CHECK_MESSAGES = {
    "izgara_yok": MESSAGES["izgara_yok"],
    "cozulemedi": "Basılı rakamlardan bulmacayı kuramadım. Daha net ya da daha yakından çekilmiş bir "
                  "fotoğraf deneyin.",
}


@app.post("/api/kontrol")
def check_upload():
    """Kalemle doldurulmuş sudokuyu kontrol eder: el yazısı her rakam doğru mu?"""
    img, error = read_upload()
    if error:
        return error
    result = check_image(img, clf, reader)
    if result.solution is None:
        return jsonify(durum=result.status, mesaj=CHECK_MESSAGES[result.status], cozum=None, sonuclar=[],
                       ozet=None, gorsel=encode_image(result.image))
    counts = {v: sum(1 for x in result.verdicts.values() if x == v) for v in ("dogru", "yanlis", "kontrol")}
    counts["bos"] = 81 - len(result.verdicts)
    return jsonify(
        durum=result.status,
        mesaj=f"{counts['dogru']} doğru, {counts['yanlis']} yanlış, "
              + (f"{counts['kontrol']} kontrol et, " if counts["kontrol"] else "") + f"{counts['bos']} boş.",
        cozum=result.solution,
        sonuclar=[{"hucre": i, "durum": v, "okunan": result.read[i]} for i, v in sorted(result.verdicts.items())],
        ozet=counts,
        gorsel=encode_image(result.image),
    )


@app.errorhandler(Exception)
def unexpected_error(e):
    """Beklenmeyen hata: kullanıcıya Türkçe mesaj; ayrıntı sadece sunucu kaydına (yol ve hata, görsel değil)."""
    if isinstance(e, HTTPException):
        return e  # 400, 404, 413 gibi bilinen durumlar kendi cevaplarıyla
    app.logger.exception("Beklenmeyen hata: %s %s", request.method, request.path)
    return jsonify(hata="Beklenmeyen bir hata oluştu. Başka bir görselle tekrar dener misin?"), 500


@app.errorhandler(413)
def too_large(_):
    return jsonify(hata="Dosya çok büyük (en fazla 20 MB)."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
