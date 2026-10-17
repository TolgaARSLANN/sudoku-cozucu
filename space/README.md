---
title: Sudoku Çözücü
emoji: 🧩
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Fotoğraftaki sudokuyu çözer, kalemle çözüleni kontrol eder
---

# Sudoku Çözücü

Sudokunun fotoğrafını ya da ekran görüntüsünü yükle: program ızgarayı bulur, rakamları okur, bulmacayı
çözer ve çözümü fotoğrafın üstüne, kağıda kalemle yazılmış gibi çizer. Kalemle doldurduğun bir sudokuyu
da kontrol eder: yanlış yazdığın rakamları kırmızıyla işaretler.

Elinde sudoku yoksa giriş ekranındaki örneklerle deneyebilirsin.

**Gizlilik:** Yüklediğin fotoğraf sadece sonucu hazırlamak için bellekte işlenir; diske kaydedilmez,
saklanmaz ve kimseyle paylaşılmaz. Sunucu kaydına IP adresi yazılmaz.

Kaynak kod, nasıl çalıştığı ve doğruluk ölçümleri: https://github.com/TolgaARSLANN/sudoku-cozucu

## Atıflar

- Örnek gazete fotoğrafları: [wichtounet/sudoku_dataset](https://github.com/wichtounet/sudoku_dataset)
  (Baptiste Wicht, Jean Hennebert), CC-BY-4.0
- El yazısı rakam ağı MNIST (Yann LeCun, Corinna Cortes, Christopher J.C. Burges; CC BY-SA 3.0) ile
  eğitildi; kalemle doldurulmuş örnek sayfa MNIST test rakamlarıyla üretildi
- Yazı tipleri: Caveat, Outfit, Work Sans (SIL Open Font License 1.1)

Tüm lisanslar: kaynak koddaki README, "Lisans ve atıflar".
