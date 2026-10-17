"""Gerçek fotoğraflarda doğruluk ölçümü.

Klasörde her foto.jpg için yanında doğru cevabı içeren foto.dat olmalı
(wichtounet/sudoku_dataset biçimi: 2 satır başlık + 9 satır rakam).

    python benchmark.py <klasör> [--hatalari-kaydet <çıktı klasörü>]
    python benchmark.py <klasör> --kontrol     # kalemle doldurulmuş sudoku kontrolü (veri/karisik, veri/dogal)
"""
import argparse
import time
from collections import Counter
from pathlib import Path

from digits import DigitClassifier
from solver import solve
from vision import load_image, save_image, solve_image


def read_truth(path):
    lines = path.read_text().splitlines()[2:11]
    return [int(v) for line in lines for v in line.split()]


def check_benchmark(photos, clf):
    """.dat yazılmış her rakamı içerir; yazılan rakam çözümdekiyle aynıysa ona "yanlış" demek yanlış alarmdır."""
    from kontrol import HandwritingReader, check_image
    reader = HandwritingReader()
    solved, verdicts = 0, Counter()
    for photo in photos:
        written = read_truth(photo.with_suffix(".dat"))
        result = check_image(load_image(str(photo)), clf, reader)
        if result.solution != solve(written):
            print(f"{photo.name}: çözüm {'bulunamadı' if result.solution is None else 'YANLIŞ'}")
            continue
        solved += 1
        for i, v in result.verdicts.items():
            if written[i]:
                verdicts[v if written[i] == result.solution[i] else f"gerçekten yanlış → {v}"] += 1
    hand = sum(n for v, n in verdicts.items() if v in ("dogru", "yanlis", "kontrol"))
    print(f"\n{len(photos)} fotoğraf")
    print(f"Doğru çözüldü       : {solved}/{len(photos)}")
    print(f"Basılı sayılan      : {verdicts['basili']}")
    print(f"El yazısı (doğru yazılmış): {hand} → 'doğru' {verdicts['dogru']}, "
          f"'kontrol et' {verdicts['kontrol']}, YANLIŞ ALARM {verdicts['yanlis']}")
    for v, n in sorted(verdicts.items()):
        if v.startswith("gerçekten"):
            print(f"Gerçekten yanlış yazılmış: {v.split('→ ')[1]} {n}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--hatalari-kaydet", dest="fail_dir")
    ap.add_argument("--kontrol", action="store_true")
    args = ap.parse_args()

    clf = DigitClassifier()
    photos = sorted(p for p in Path(args.folder).glob("*.jpg") if p.with_suffix(".dat").exists())
    if args.kontrol:
        return check_benchmark(photos, clf)
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
