# Sudoku Çözücü

Sudokunun fotoğrafını ya da ekran görüntüsünü ver; program ızgarayı bulur, rakamları okur,
bulmacayı çözer ve çözümü **fotoğrafın üstüne, perspektife uygun şekilde** çizer.

Derin öğrenme kütüphanesi kullanmaz: görüntü işleme OpenCV ile, rakam tanıma ise bilgisayardaki
fontlardan üretilen sentetik veriyle eğitilen bir k-NN sınıflandırıcıyla yapılır.

## Özellikler

- **Web arayüzü:** sürükle-bırak, dosya seçme ya da `Ctrl+V` ile ekran görüntüsü yapıştırma
- **Kurallarla hata düzeltme:** emin olunmadan okunan rakamlar sudoku kurallarına göre düzeltilir
  ve turuncu gösterilir
- **Düzeltme modu:** okunamayan rakamı tahtada elle düzeltip tekrar çözdürme; emin olunmayan
  hücreler sarıyla işaretlenir
- **Eğik, yan ya da ters çekilmiş fotoğraflar:** perspektif düzeltme ve otomatik yön bulma
- **Yanlış cevap vermez:** okunan tahtanın tek çözümü yoksa çözüm göstermek yerine uyarır
- **Komut satırı ve canlı kamera modu**

## Kurulum

```
pip install -r requirements.txt
```

## Kullanım

**Web arayüzü:**

```
python app.py
```

Ardından tarayıcıda <http://127.0.0.1:5000> adresini aç.

Arayüz React + TypeScript ile yazılmıştır (`frontend/`). Derlenmiş hali `static/` klasöründe hazır
gelir; sadece kullanmak için Node.js gerekmez. Arayüzü değiştirmek için:

```
cd frontend
npm install
npm run dev     # canlı geliştirme: http://localhost:5173 (app.py ayrıca çalışıyor olmalı)
npm run build   # değişiklikleri static/ klasörüne derler
```

`static/` klasörü derleme çıktısıdır, elle düzenlenmez.

**Komut satırı:**

```
python cli.py                   # dosya seçme penceresi açılır
python cli.py foto.jpg          # sonucu foto_cozum.jpg olarak kaydeder
python cli.py *.jpg --gosterme  # toplu çözüm, pencere açmadan
python cli.py --kamera          # canlı kamera (çıkış: q)
```

## Nasıl çalışır?

1. **Izgarayı bulma** (`vision.find_grid`): Görüntü uyarlamalı eşiklemeyle siyah-beyaza çevrilir,
   konturlar bulunur. Her büyük dörtgen düzleştirilir ve iç çizgilerin gerçekten 1/9 aralıklarla
   durup durmadığı puanlanır. Böylece kağıt kenarı, tek bir 3x3 kutu ya da sayfadaki küçük
   "dünkü çözüm" ızgarası asıl bulmacayla karışmaz. Kenarı kopuk ızgaralar için konturun dış
   bükey zarfı kullanılır.
2. **Düzleştirme:** Izgara 450x450'lik bir kareye çevrilip 81 hücreye bölünür.
3. **Rakam okuma** (`vision.find_digits`, `vision.read_board`): Izgara çizgileri morfolojik
   açma ile silinir. Hücre sınırlarına körü körüne güvenilmez: tüm tahtada rakam boyutundaki
   parçalar bulunur ve merkezlerinin düştüğü hücreye atanır. Böylece köşeler biraz kaymış ya da
   sayfa hafif kıvrık olsa da rakamlar kaybolmaz. Rakamlar 28x28'e normalize edilir ve en yakın
   örneğe göre sınıflandırılır. Tahta 4 yönde okunur, rakamların en net tanındığı yön seçilir.
4. **Çözme** (`solver.solve_unique`): Bitmask ile çalışan, her adımda en az seçenekli hücreyi
   seçen (MRV) geri izlemeli (backtracking) bir çözücü. Arama ikinci bir çözüm için de sürer:
   birden fazla çözüm çıkması bir rakamın okunamadığını gösterir.
5. **Kurallarla düzeltme** (`vision.correct_and_solve`): Tahta çözülemezse, sınıflandırıcının emin
   olmadığı hücrelerde (1. ve 2. tahmini birbirine yakın olanlar) 2. ve 3. tahminler en olasıdan
   başlayarak denenir. Bir değişiklik ancak bulmacayı tek çözümlü yapıyorsa kabul edilir.
   Emin okunmuş rakamlara hiç dokunulmaz: birden çok hata varken onları değiştirmek tutarlı ama
   yanlış bir tahta üretebiliyor.
6. **Geri yansıtma:** Çözüm düz karenin üstüne çizilir ve ters perspektif dönüşümüyle orijinal
   fotoğrafa yerleştirilir.

**Rakam tanıma verisi** (`digits.py`): Windows fontlarıyla (116 font) 1-9 rakamları çizilir.
Döndürme, kalınlık değişimi ve düşük çözünürlük/bulanıklık ile çoğaltılarak 7162 örnek elde edilir.
Hazır veri `digits_data.npz` dosyasında gelir. Yeniden üretmek için `python digits.py` (Windows gerekir).

## Doğruluk

[wichtounet/sudoku_dataset](https://github.com/wichtounet/sudoku_dataset) içindeki, telefonla
çekilmiş gerçek gazete fotoğraflarıyla ölçülmüştür:

| | Geliştirmede kullanılan 40 fotoğraf | Hiç görülmemiş 40 fotoğraf |
|---|---|---|
| Izgara bulundu | 40 | 38 |
| Doğru çözüldü | 35 | 36 |
| **Yanlış çözüm gösterildi** | **0** | **0** |

Ayarlar yalnızca ilk sette yapıldı; ikinci set ezber olup olmadığını kontrol etmek için ayrı tutuldu.

Çözülemeyen fotoğraflarda program yanlış cevap vermez, "okunamadı" der. Web arayüzünde eksik
rakam elle düzeltilip çözüm alınabilir. Ekran görüntülerinde ve net fotoğraflarda doğruluk çok
daha yüksektir.

Bu ölçümü kendin tekrarlamak için fotoğrafları indir (yaklaşık 18 MB, `veri/` klasörüne):

```
python veri_indir.py
python benchmark.py veri/gelistirme
python benchmark.py veri/dogrulama
```

Fotoğraflar Baptiste Wicht ve Jean Hennebert'in veri setinden alınmıştır ve
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) lisanslıdır.

Kendi fotoğraf setinle de ölçebilirsin: her `foto.jpg` dosyasının yanında doğru cevabı içeren bir
`foto.dat` olmalı (2 satır başlık ve ardından 9 satır rakam).

## Testler

```
python -m pytest
```

Çözücü, sentetik eğik fotoğraflar, gerçek ekran görüntüleri ve web API'si test edilir. Tarayıcı
testleri (`tests/test_browser.py`) arayüzü gerçek bir tarayıcıda uçtan uca dener: görsel yükleme,
düzeltme modu, ok tuşları, telefon görünümü, hata durumları. Kurulu Microsoft Edge'i kullanır;
Edge yoksa `python -m playwright install chromium` gerekir. Playwright kurulu değilse bu testler atlanır.

## Proje yapısı

```
app.py            web sunucusu (Flask)
frontend/         web arayüzünün kaynak kodu (React + TypeScript + Vite)
static/           derlenmiş arayüz (npm run build çıktısı)
cli.py            komut satırı ve kamera modu
vision.py         ızgara bulma, rakam okuma, çözümü çizme
digits.py         sentetik veri üretimi ve k-NN rakam tanıma
solver.py         sudoku çözücü
benchmark.py      gerçek fotoğraflarda doğruluk ölçümü
veri_indir.py     ölçümde kullanılan 80 fotoğrafı indirir
tests/            otomatik testler
```

## Sınırlamalar

- Yalnızca basılı rakamları okur; elle yazılmış rakamları tanımaz.
- Çok kıvrık sayfalarda ızgara düz bir dörtgen olmadığı için kenardaki hücreler kayabilir.
- Rakam veri setini yeniden üretmek Windows fontları gerektirir (hazır veri her sistemde çalışır).
