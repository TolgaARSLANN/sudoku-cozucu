"""Web arayüzünün gerçek bir tarayıcıda uçtan uca testleri (Playwright).

Playwright ya da tarayıcı yoksa testler atlanır. Kurulum:
    pip install playwright
    python -m playwright install chromium   # Microsoft Edge kuruluysa gerekmez
"""
import json
import threading
import time
from pathlib import Path

import numpy as np
import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from werkzeug.serving import make_server  # noqa: E402

from app import app  # noqa: E402
from test_pipeline import PUZZLE, grid_image  # noqa: E402
from vision import save_image  # noqa: E402

ROOT = Path(__file__).parent.parent
IMAGES = Path(__file__).parent / "images"
HOLES = (0, 1, 4, 9, 12, 13)  # bu ipuçları silinince bulmacanın birden fazla çözümü olur


@pytest.fixture(scope="module")
def server():
    """Flask uygulamasını boş bir portta arka planda çalıştırır."""
    if not (ROOT / "static" / "index.html").exists():
        pytest.skip("Arayüz derlenmemiş: frontend klasöründe 'npm run build' çalıştır.")
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        for options in ({"channel": "msedge"}, {}):  # önce kurulu Edge, yoksa Playwright'ın Chromium'u
            try:
                b = p.chromium.launch(**options)
                break
            except Exception:
                continue
        else:
            pytest.skip("Tarayıcı bulunamadı: 'python -m playwright install chromium' çalıştır.")
        yield b
        b.close()


def open_page(browser, server, *, mobile=False):
    width, height = (375, 812) if mobile else (1280, 900)
    context = browser.new_context(viewport={"width": width, "height": height}, has_touch=mobile, is_mobile=mobile)
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(server)
    return page


@pytest.fixture
def page(browser, server):
    page = open_page(browser, server)
    yield page
    assert page.errors == [], f"Sayfada JavaScript hatası: {page.errors}"
    page.context.close()


@pytest.fixture
def unsolvable_image(tmp_path):
    """Birkaç ipucu eksik, bu yüzden tek çözümü olmayan bir sudoku görseli."""
    puzzle = "".join("0" if i in HOLES else ch for i, ch in enumerate(PUZZLE))
    path = tmp_path / "eksik.jpg"
    save_image(str(path), grid_image(puzzle, r"C:\Windows\Fonts\arial.ttf"))
    return path


def test_home_page(page):
    assert page.inner_text("h1") == "Fotoğraftaki sudokuyu çöz, çözümü üstüne çizelim"
    assert page.is_visible("#drop")
    assert len(page.query_selector_all("#demo-board .cell")) == 81


def test_mobile_layout(browser, server):
    page = open_page(browser, server, mobile=True)
    assert page.inner_text(".drop-title").strip() == "Sudoku görseli seç"  # "sürükle bırak" telefonda anlamsız
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "yatay kaydırma var"
    page.context.close()


def test_solves_uploaded_image(page):
    page.set_input_files("#file", IMAGES / "ekran_1.jpg")
    page.wait_for_selector("#result")
    assert page.inner_text("#status") == "Çözüldü."
    givens = len(page.query_selector_all("#board .given"))
    assert givens > 0 and givens + len(page.query_selector_all("#board .solved")) == 81
    assert f"{givens} rakam okundu" in page.text_content("#stats")
    assert "primary" in page.get_attribute("#download", "class")


def test_fix_mode(page, unsolvable_image):
    page.set_input_files("#file", unsolvable_image)
    page.wait_for_selector("#result")
    assert page.inner_text("#status").startswith("Rakamların bir kısmı okunamadı")
    assert page.inner_text("#board-title") == "Okunan rakamlar"

    inputs = page.query_selector_all("#board input")
    inputs[10].focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowDown")
    assert page.evaluate("[...document.querySelectorAll('#board input')].indexOf(document.activeElement)") == 20

    for i in HOLES:  # eksik ipuçlarını kullanıcı gibi geri yaz
        inputs[i].fill(PUZZLE[i])
    photo_before = page.get_attribute("#photo", "src")
    page.click("#fix")
    page.wait_for_selector("#board .solved")
    assert page.inner_text("#status") == "Çözüldü."
    assert page.inner_text("#board-title") == "Çözüm"
    # Çözüm fotoğrafa da çizilmeli; indirilen görsel çözümsüz kalmamalı
    assert page.get_attribute("#photo", "src") != photo_before
    assert page.get_attribute("#download", "href") == page.get_attribute("#photo", "src")


def test_shows_rule_corrections(page):
    # Sunucu cevabı taklit edilir: arayüzün düzeltmeleri nasıl gösterdiği test edilir
    board = [int(c) for c in PUZZLE]
    board[4] = 7
    fake = {"durum": "cozuldu", "mesaj": "Çözüldü.", "tahta": board, "cozum": board,
            "duzeltilen": [{"hucre": 4, "okunan": 1}], "emin_degil": [], "koseler": None, "adimlar": [],
            "gorsel": "data:image/gif;base64,R0lGODlhAQABAAAAACw="}
    page.route("**/api/coz", lambda route: route.fulfill(content_type="application/json", body=json.dumps(fake)))
    page.set_input_files("#file", IMAGES / "ekran_1.jpg")
    page.wait_for_selector("#result")
    assert len(page.query_selector_all("#board .corrected")) == 1
    assert "1. satır 5. sütun: 1 okundu, 7 olmalı" in page.inner_text("#fixes")


def test_steps_panel(page):
    page.set_input_files("#file", IMAGES / "ekran_1.jpg")
    page.wait_for_selector("#result")
    assert page.get_attribute("#steps", "open") is None  # çözüldüyse kapalı gelir
    page.click("#steps summary")
    titles = [t.inner_text() for t in page.query_selector_all("#steps .step h3")]
    assert titles == ["Siyah-beyaz görüntü", "Izgara adayları", "Düzleştirilmiş tahta",
                      "Izgara çizgileri silindi", "Okunan rakamlar"]
    assert all(img.is_visible() for img in page.query_selector_all("#steps .step img"))


def test_steps_panel_explains_missing_grid(page, tmp_path):
    blank = tmp_path / "bos.jpg"
    save_image(str(blank), np.full((480, 640, 3), 200, np.uint8))
    page.set_input_files("#file", blank)
    page.wait_for_selector("#result")
    assert page.get_attribute("#steps", "open") is not None  # ızgara yoksa sebebi görünsün diye açık
    assert len(page.query_selector_all("#steps .step")) == 2


def test_rejects_non_image(page, tmp_path):
    text_file = tmp_path / "not.txt"
    text_file.write_text("x")
    page.set_input_files("#file", text_file)
    assert "görsel dosyası değil" in page.inner_text("#status")
    assert page.is_visible("#hero")


def test_single_request_while_busy(page):
    calls = []
    page.on("request", lambda r: calls.append(r.url) if r.url.endswith("/api/coz") else None)
    page.route("**/api/coz", lambda route: (time.sleep(1), route.continue_()))
    page.set_input_files("#file", IMAGES / "ekran_1.jpg")
    page.wait_for_selector("#loading")
    page.set_input_files("#file", IMAGES / "ekran_2.jpg")  # istek sürerken ikinci yükleme yok sayılmalı
    page.wait_for_selector("#result")
    assert len(calls) == 1


def test_drag_overlay(page):
    page.evaluate("""() => {
        const dt = new DataTransfer();
        dt.items.add(new File(['x'], 'a.png', {type: 'image/png'}));
        window.dispatchEvent(new DragEvent('dragenter', {dataTransfer: dt}));
    }""")
    assert page.is_visible("#drop-overlay")
    page.evaluate("window.dispatchEvent(new DragEvent('dragleave'))")
    assert page.is_hidden("#drop-overlay")
