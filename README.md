# Sudoku Çözücü

Sudokunun fotoğrafını ya da ekran görüntüsünü ver; program ızgarayı bulur, rakamları okur,
bulmacayı çözer ve çözümü **fotoğrafın üstüne, kağıda kalemle yazılmış gibi** çizer.

Kalemle doldurulmuş bir sudokuyu da **kontrol eder**: el yazısı rakamları okur ve yanlış
yazılanları bulur.

Çalışırken derin öğrenme kütüphanesi gerektirmez: görüntü işleme OpenCV ile, basılı rakam tanıma
bilgisayardaki fontlardan üretilen sentetik veriyle eğitilen bir k-NN sınıflandırıcıyla yapılır.
El yazısı için küçük bir sinir ağı PyTorch ile eğitilip ONNX olarak projeye konmuştur; OpenCV'nin
`cv2.dnn` modülüyle çalıştırılır.

## Özellikler

- **Web arayüzü:** sürükle-bırak, dosya seçme ya da `Ctrl+V` ile ekran görüntüsü yapıştırma
- **Kurallarla hata düzeltme:** emin olunmadan okunan rakamlar sudoku kurallarına göre düzeltilir
  ve turuncu gösterilir
- **Düzeltme modu:** okunamayan rakamı tahtada elle düzeltip tekrar çözdürme; emin olunmayan
  hücreler sarıyla işaretlenir
- **İpucu modu ve zorluk derecesi:** çözümü hamle hamle açar; her hamlede hangi tekniğin
  (tek aday, gizli tek, açık çift, kutu-satır kesişimi, gizli çift, açık üçlü, X-Wing) neden işe
  yaradığını anlatır. Bulmacaya, gereken en zor tekniğe göre Kolay / Orta / Zor / Şeytani der.
  Oynatıcıyla çözüm hamle hamle kendiliğinden ilerler (hız seçimi ve kaydırıcıyla atlama).
- **Fotoğraf kalite önerileri:** okuma başarısız olursa olası sebebi (bulanıklık, küçük ızgara,
  karanlık, parlama) ve ne yapılacağını söyler
- **"Nasıl gördüm?" paneli:** fotoğrafın adım adım nasıl işlendiğini gösterir (siyah-beyaz görüntü,
  puanlanan ızgara adayları, düzleştirilmiş tahta, silinen çizgiler, okunan rakamlar ve güven
  durumu); ızgara bulunamazsa sebebini görmeyi sağlar
- **Eğik, yan ya da ters çekilmiş fotoğraflar:** perspektif düzeltme ve otomatik yön bulma
- **Yanlış cevap vermez:** okunan tahtanın tek çözümü yoksa çözüm göstermek yerine uyarır
- **Kalemle doldurulmuş sudokuyu kontrol etme:** giriş ekranında "Kalemle doldurdum, kontrol et"
  seçilir. El yazısı her rakam için "doğru", "yanlış" ya da "kontrol et" der; yanlışlar fotoğrafın
  üstünde kırmızı halkayla, tahtada kırmızıyla işaretlenir ve "22 doğru, 2 yanlış, 11 boş" gibi
  özetlenir. Doğru cevaplar istenirse ayrıca açılır. Ağ okuduğundan emin değilse "yanlış" demez.
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
   bükey zarfı kullanılır; bulanık fotoğraflarda kesik kesik kalan ince çizgiler için eşiklenmiş
   görüntünün hafifçe kalınlaştırılmış halinden de aday üretilir.
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
6. **Geri yansıtma** (`vision.draw_handwritten`): Çözüm el yazısı bir yazı tipiyle, ızgaranın
   fotoğraftaki gerçek boyutunda çizilir ve ters perspektif dönüşümüyle fotoğrafa yerleştirilir.
   Her rakam biraz farklı açı, boyut ve kalem baskısıyla yazılır. Mürekkep kağıdın üstüne
   yapıştırılmaz, kağıdı koyulaştırır (çarpma karışımı); böylece kağıdın dokusu, gölgesi ve ışığı
   korunur. Canlı kamera modunda görünürlük için yeşil dijital rakamlar kullanılır.

### Kalemle doldurulmuş sudokuyu kontrol etme (`kontrol.py`)

1. **El yazısı okuma:** Basılı rakamlar için kullanılan ikili maske ince el yazısını kalınlaştırıp
   delikleri dolduruyor (8 → 1 gibi). El yazısı ağına bunun yerine gri mürekkep yoğunluğu verilir,
   sadece rakamın kendi maskesinin çevresinden; böylece ızgara çizgisi parçaları ağa gitmez.
   Izgara çizgisi silme de sadece hücre sınırına yakın çizgileri siler: büyük yazılmış bir 1'in
   ya da 7'nin uzun gövdesi çizgi sanılıp silinmez.
2. **Sinir ağı** (`egit_el_yazisi.py`): 4 evrişim katmanlı küçük bir ağ, MNIST el yazısı rakamlarıyla
   eğitilir. Fotoğrafa benzetmek için döndürme, eğme, kalın/ince kalem, bulanıklık, soluk mürekkep ve
   gürültü eklenir; MNIST'te az bulunan Türk/Avrupa yazımları (ortası çizgili 7, bayraklı 1) için ek
   örnekler üretilir. Model, el yazısı eklenmiş gazete fotoğraflarıyla seçilir.
3. **Basılı mı el yazısı mı:** Bir rakamın yazı tipine uzaklığı tek başına yetmiyor (bulanık
   fotoğrafta basılı rakamlar da uzaklaşıyor). Bunun yerine aynı fotoğraftaki basılı rakamlara
   *göre* uzaklık, yükseklik ve çizgi kalınlığı farkına bakan bir lojistik regresyon kullanılır.
4. **Bulmacayı kurma:** Rakamlar en güvenilirden başlanarak ipucu yapılır: önce yazı tipi
   okuyucusuyla el yazısı ağının aynı okuduğu rakamlar (basılı rakamları ikisi de tanır), sonra
   basılı olma ihtimaline göre. Çelişki çıkaran rakam ipucu yapılmaz; tek çözüm bulununca durulur.
   Böylece basılı sanılıp yanlış okunan bir el yazısı rakam bulmacayı bozmaz.
5. **Hüküm:** Ağ çözümdeki rakama en az %10 olasılık veriyorsa "doğru"; vermiyorsa ve okuduğu
   rakamdan en az %98 eminse "yanlış"; ikisi de değilse "kontrol et".

Modeli yeniden eğitmek için (PyTorch sadece burada gerekir, ~15 dk CPU):

```
pip install -r requirements-egitim.txt
python veri_indir.py
python egit_el_yazisi.py
```

**Rakam tanıma verisi** (`digits.py`): Windows fontlarıyla (116 font) 1-9 rakamları çizilir.
Döndürme, kalınlık değişimi ve düşük çözünürlük/bulanıklık ile çoğaltılarak 7162 örnek elde edilir.
Hazır veri `digits_data.npz` dosyasında gelir. Yeniden üretmek için `python digits.py` (Windows gerekir).

## Doğruluk

[wichtounet/sudoku_dataset](https://github.com/wichtounet/sudoku_dataset) içindeki, telefonla
çekilmiş gerçek gazete fotoğraflarıyla ölçülmüştür:

| | Geliştirmede kullanılan 40 fotoğraf | Hiç görülmemiş 40 fotoğraf |
|---|---|---|
| Izgara bulundu | 40 | 40 |
| Doğru çözüldü | 36 | 37 |
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

### Kalemle doldurulmuş sudoku kontrolü

Aynı gazete fotoğraflarının, boş hücrelerine sonradan el yazısı eklenmiş halleriyle
(`veri/karisik/`) ve 5 gerçek tükenmez kalem fotoğrafıyla (`veri/dogal/`) ölçülmüştür:

| | Geliştirme (40) | Doğrulama (40) | Gerçek kalem (5) |
|---|---|---|---|
| Bulmaca doğru çözüldü | 39 | 40 | 5 |
| Yanlış çözüm | 1 | 0 | 0 |
| El yazısı rakam | 1983 | 2073 | 205 |
| → "doğru" | 1963 | 2047 | 200 |
| → "kontrol et" | 14 | 23 | 4 |
| → **doğru yazılmışa "yanlış" (yanlış alarm)** | **6** | **3** | **1** |

Yanlış yazılmış rakam benzetimiyle (fotoğraf başına 3 rakam), yanlışların yaklaşık %90'ı "yanlış",
%6-7'si "kontrol et" olarak işaretlendi.

Dürüst notlar: Bulmacayı kurma sırası doğrulama setindeki hatalara bakılarak düzeltildi; o set
artık tamamen "görülmemiş" sayılmaz. Gerçek kalem seti sadece 5 fotoğraf ve ayarlarda kullanıldı.
Geliştirme setindeki tek yanlış çözümde, el yazısı bir rakamı iki okuyucu da %99 güvenle yanlış okuyor.

```
python benchmark.py veri/karisik/dogrulama --kontrol
python benchmark.py veri/dogal --kontrol
```

Kendi fotoğraf setinle de ölçebilirsin: her `foto.jpg` dosyasının yanında doğru cevabı içeren bir
`foto.dat` olmalı (2 satır başlık ve ardından 9 satır rakam).

## Testler

```
python -m pytest
```

Çözücü, sentetik eğik fotoğraflar, gerçek ekran görüntüleri, kalemle doldurulmuş sayfa kontrolü
ve web API'si test edilir. Tarayıcı
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
adimlar.py        "Nasıl gördüm?" paneli için açıklamalı ara görseller
kalite.py         fotoğraf kalite kontrolü (bulanıklık, ızgara boyutu, karanlık, parlama)
fonts/            el yazısı yazı tipi Caveat (SIL Open Font License, fonts/OFL.txt)
digits.py         sentetik veri üretimi ve k-NN rakam tanıma
kontrol.py        kalemle doldurulmuş sudokuyu kontrol etme
egit_el_yazisi.py el yazısı ağını eğitir (el_yazisi.onnx, el_yazisi_tur.json)
solver.py         sudoku çözücü (deneme yanılma, tek çözüm doğrulaması)
ipucu.py          insan gibi çözen çözücü: ipuçları ve zorluk derecesi
benchmark.py      gerçek fotoğraflarda doğruluk ölçümü
veri_indir.py     ölçümde kullanılan 80 fotoğrafı indirir
tests/            otomatik testler
```

## Sınırlamalar

- Çözme modu yalnızca basılı rakamları okur; el yazısı sadece kontrol modunda okunur.
- El yazısı kontrolü az sayıda gerçek kalem fotoğrafıyla denendi; farklı el yazılarında doğruluk değişebilir.
- Çok kıvrık sayfalarda ızgara düz bir dörtgen olmadığı için kenardaki hücreler kayabilir.
- Rakam veri setini yeniden üretmek Windows fontları gerektirir (hazır veri her sistemde çalışır).
