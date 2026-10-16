"""Doğruluk ölçümünde kullanılan 80 gerçek sudoku fotoğrafını indirir.

Kaynak: wichtounet/sudoku_dataset (Baptiste Wicht, Jean Hennebert), CC-BY-4.0 lisansı.
Gazete sudokularının telefonla çekilmiş fotoğrafları ve her birinin doğru cevabı (.dat).

    python veri_indir.py
    python benchmark.py veri/dogrulama

gelistirme: ayarlar bu 40 fotoğrafa bakılarak yapıldı.
dogrulama : ezber kontrolü için ayrı tutulan 40 fotoğraf; ayarlarda hiç kullanılmadı.
"""
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/wichtounet/sudoku_dataset/master/images/image{}{}"
FOLDER = Path(__file__).parent / "veri"
SETS = {
    "gelistirme": [11, 16, 26, 31, 50, 65, 74, 80, 84, 87, 93, 95, 97, 103, 104, 153, 155, 156, 157, 159,
                   167, 168, 170, 180, 181, 186, 198, 200, 209, 1001, 1031, 1036, 1038, 1039, 1040, 1049,
                   1050, 1055, 1076, 1078],
    "dogrulama": [8, 17, 22, 25, 29, 37, 58, 61, 71, 77, 91, 102, 105, 106, 111, 129, 134, 145, 161, 165,
                  166, 172, 173, 183, 189, 211, 1003, 1004, 1005, 1008, 1020, 1022, 1041, 1045, 1059, 1067,
                  1073, 1080, 1083, 1088],
}


def main():
    for name, numbers in SETS.items():
        target = FOLDER / name
        target.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        for n in numbers:
            for ext in (".jpg", ".dat"):
                path = target / f"image{n}{ext}"
                if path.exists():
                    continue
                try:
                    urllib.request.urlretrieve(URL.format(n, ext), path)
                except OSError as e:
                    path.unlink(missing_ok=True)  # yarım kalan dosya ölçümü bozmasın
                    sys.exit(f"{path.name} indirilemedi ({e}). İnternet bağlantısını kontrol edip tekrar çalıştır.")
                downloaded += 1
        print(f"{name}: {len(numbers)} fotoğraf hazır ({downloaded} dosya indirildi) → {target}")


if __name__ == "__main__":
    main()
