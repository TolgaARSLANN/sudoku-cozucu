"""Gerçek fotoğraflarda doğruluk ölçümü.

Klasörde her foto.jpg için yanında doğru cevabı içeren foto.dat olmalı
(wichtounet/sudoku_dataset biçimi: 2 satır başlık + 9 satır rakam).

    python benchmark.py <klasör> [--hatalari-kaydet <çıktı klasörü>]
"""
import argparse
import time
from pathlib import Path

from digits import DigitClassifier
from solver import solve
from vision import load_image, save_image, solve_image


def read_truth(path):
    lines = path.read_text().splitlines()[2:11]
    return [int(v) for line in lines for v in line.split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--hatalari-kaydet", dest="fail_dir")
    args = ap.parse_args()

    clf = DigitClassifier()
    photos = sorted(p for p in Path(args.folder).glob("*.jpg") if p.with_suffix(".dat").exists())
    stats = dict(grid=0, perfect=0, solved=0, false=0, corrected=0, missed=0, extra=0, wrong=0, digits=0)
    start = time.time()
    for photo in photos:
        truth = read_truth(photo.with_suffix(".dat"))
        result = solve_image(load_image(str(photo)), clf)
        stats["digits"] += sum(1 for t in truth if t)
        if result.status == "izgara_yok":
            print(f"{photo.name}: ızgara bulunamadı")
        else:
            stats["grid"] += 1
            missed = sum(1 for t, b in zip(truth, result.board) if t and not b)
            extra = sum(1 for t, b in zip(truth, result.board) if b and not t)
            wrong = sum(1 for t, b in zip(truth, result.board) if t and b and t != b)
            stats["missed"] += missed
            stats["extra"] += extra
            stats["wrong"] += wrong
            stats["perfect"] += result.board == truth
            # Bir rakam kaçsa bile çözüm hâlâ tek ve doğru olabilir; asıl tehlike yanlış çözüm göstermek
            if result.status == "cozuldu":
                correct = result.solution == solve(truth)
                stats["solved"] += correct
                stats["false"] += not correct
            stats["corrected"] += len(result.corrected)
            if result.board != truth:
                print(f"{photo.name}: {missed} kaçırılan, {extra} hayalet, {wrong} yanlış rakam")
        if args.fail_dir and (result.status != "cozuldu" or result.board != truth):
            Path(args.fail_dir).mkdir(exist_ok=True)
            save_image(str(Path(args.fail_dir) / photo.name), result.image)

    n = len(photos)
    print(f"\n{n} fotoğraf, {time.time() - start:.1f} sn")
    print(f"Izgara bulundu      : {stats['grid']}/{n}")
    print(f"Tüm rakamlar doğru  : {stats['perfect']}/{n}")
    print(f"Doğru çözüldü       : {stats['solved']}/{n}")
    print(f"YANLIŞ çözüm gösterildi: {stats['false']}/{n}  (hedef: 0)")
    print(f"Kurallarla düzeltilen rakam: {stats['corrected']}")
    print(f"Rakam hataları      : {stats['missed']} kaçırılan, {stats['extra']} hayalet, "
          f"{stats['wrong']} yanlış (toplam {stats['digits']} rakam)")


if __name__ == "__main__":
    main()
