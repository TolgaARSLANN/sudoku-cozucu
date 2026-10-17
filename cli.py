"""Sudoku Çözücü - komut satırı.

    python cli.py                   # dosya seçme penceresi açılır
    python cli.py foto.jpg [...]    # bir ya da daha fazla görsel
    python cli.py --kamera          # canlı kamera (çıkış: q)
"""
import argparse
from pathlib import Path

import cv2

from digits import DigitClassifier
from ipucu import explain
from kalite import WARNINGS, check_quality
from vision import MESSAGES, SolutionCache, limit_size, load_image, process_frame, save_image, solve_image


def format_board(board):
    lines = []
    for r in range(9):
        if r in (3, 6):
            lines.append("------+-------+------")
        row = [str(v) if v else "." for v in board[r * 9:(r + 1) * 9]]
        lines.append(" | ".join(" ".join(row[i:i + 3]) for i in (0, 3, 6)))
    return "\n".join(lines)


def pick_files():
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    paths = filedialog.askopenfilenames(
        title="Sudoku görseli seç",
        filetypes=[("Görseller", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Tüm dosyalar", "*.*")])
    root.destroy()
    return list(paths)


def show(img):
    """Telefon fotoğrafları ekrandan büyük olabilir; pencereye sığacak kadar küçültür."""
    h, w = img.shape[:2]
    scale = min(1.0, 900 / h, 1400 / w)
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    cv2.imshow("Sudoku Cozucu (kapatmak icin bir tusa basin)", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def solve_files(paths, clf, show_window):
    for path in map(Path, paths):
        img = load_image(str(path))
        if img is None:
            print(f"\n{path.name}: görüntü okunamadı.")
            continue
        result = solve_image(limit_size(img), clf)
        print(f"\n{path.name}: {MESSAGES[result.status]}")
        if result.solution:
            print(f"  Zorluk: {explain(result.board)['zorluk']}")
        if result.status != "cozuldu":
            for problem in check_quality(img, result.corners):
                print(f"  İpucu: {WARNINGS[problem]}")
        for i, old in result.corrected.items():
            r, c = divmod(i, 9)
            print(f"  Düzeltildi: {r + 1}. satır {c + 1}. sütun {old} okundu, kurallara göre {result.board[i]}")
        if result.board:
            print(format_board(result.solution or result.board))
        out = path.with_name(path.stem + "_cozum.jpg")
        save_image(str(out), result.image)
        print(f"Kaydedildi: {out}")
        if show_window:
            show(result.image)


def run_camera(clf):
    cache = SolutionCache()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Kamera açılamadı.")
        return
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("Sudoku Cozucu - kamera (q: cikis)", process_frame(frame, clf, cache))
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser(description="Fotoğraftaki sudokuyu okur, çözer ve çözümü üstüne çizer.")
    ap.add_argument("gorseller", nargs="*", help="çözülecek görsel(ler); verilmezse dosya seçme penceresi açılır")
    ap.add_argument("--kamera", action="store_true", help="canlı kamera modu")
    ap.add_argument("--gosterme", action="store_true", help="sonuç penceresini açma, sadece kaydet")
    args = ap.parse_args()

    clf = DigitClassifier()
    if args.kamera:
        run_camera(clf)
        return
    paths = args.gorseller or pick_files()
    if not paths:
        print("Görsel seçilmedi.")
        return
    solve_files(paths, clf, show_window=not args.gosterme and len(paths) == 1)


if __name__ == "__main__":
    main()
