import type { KeyboardEvent } from "react";
import { Board } from "./Board";
import { Icon, type IconName } from "./Icon";

export type Task = "coz" | "kontrol";

// Örnek: ünlü bir bulmaca ve çözümü; iki rakam "kurallarla düzeltilmiş" olarak gösterilir
const DEMO = [..."530070000600195000098000060800060003400803001700020006060000280000419005000080079"].map(Number);
const DEMO_SOLUTION = [..."534678912672195348198342567859761423426853791713924856961537284287419635345286179"].map(Number);
const DEMO_CORRECTED = [{ hucre: 4, okunan: 1 }, { hucre: 31, okunan: 8 }];

const FEATURES: { icon: IconName; title: string; text: string }[] = [
  { icon: "scan", title: "Eğik ve ters fotoğraflar",
    text: "Perspektifi düzeltir, fotoğraf yan ya da ters çekilmiş olsa bile doğru yönü kendisi bulur." },
  { icon: "shield", title: "Yanlış çözüm göstermez",
    text: "Okuduğu tahtanın tek bir çözümü olduğunu doğrular. Emin değilse tahmin yürütmez, söyler." },
  { icon: "pencil", title: "Kolayca düzelt",
    text: "Okunamayan bir rakam olursa tahtada düzeltip tek tıkla tekrar çözdürebilirsin." },
  { icon: "check", title: "Kalemle çözdüğünü kontrol et",
    text: "El yazını okur, yanlış yazdığın rakamları fotoğrafın üstünde kırmızıyla işaretler." },
];

interface HeroProps {
  onPick: () => void;
  busy: boolean;
  task: Task;
  onTaskChange: (task: Task) => void;
}

export function Hero({ onPick, busy, task, onTaskChange }: HeroProps) {
  // Etiket bir buton gibi davranır: Enter ve Boşluk dosya seçiciyi açar
  function handleKey(e: KeyboardEvent<HTMLLabelElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onPick();
    }
  }

  return (
    <section id="hero" aria-labelledby="hero-title">
      <div className="hero">
        <div>
          <span className="eyebrow"><Icon name="sparkle" />Fotoğraftan çözüme, saniyeler içinde</span>
          <h1 id="hero-title">Fotoğraftaki sudokuyu çöz, çözümü üstüne çizelim</h1>
          <p className="lead">
            {task === "coz"
              ? "Gazeteden çektiğin fotoğrafı ya da bir ekran görüntüsünü yükle. Rakamları okur, bulmacayı çözer ve " +
                "sonucu fotoğrafın üzerine yerleştirir."
              : "Kalemle doldurduğun sudokunun fotoğrafını yükle. El yazını okur, yanlış yazdığın rakamları " +
                "fotoğrafın üstünde kırmızıyla işaretler."}
          </p>

          {/* Seçim yapıştırma ve sürükle-bırak için de geçerli */}
          <div className="segmented task" role="group" aria-label="Ne yapılsın?">
            <button type="button" id="task-solve" aria-pressed={task === "coz"} onClick={() => onTaskChange("coz")}>
              Çöz
            </button>
            <button type="button" id="task-check" aria-pressed={task === "kontrol"}
                    onClick={() => onTaskChange("kontrol")}>
              Kalemle doldurdum, kontrol et
            </button>
          </div>

          <label id="drop" htmlFor="file" tabIndex={0} role="button" aria-busy={busy}
                 aria-describedby="drop-hint drop-meta" onKeyDown={handleKey}>
            <span className="drop-icon"><Icon name="upload" /></span>
            <span className="drop-title">
              <span className="hint-desktop">
                {task === "coz" ? "Görseli sürükleyip bırak" : "Doldurduğun sudokunun fotoğrafını bırak"}
              </span>
              <span className="hint-touch">{task === "coz" ? "Sudoku görseli seç" : "Doldurduğun sudokuyu seç"}</span>
            </span>
            <span className="drop-hint" id="drop-hint">
              <span className="hint-desktop">ya da ekran görüntüsünü <kbd>Ctrl</kbd> + <kbd>V</kbd> ile yapıştır</span>
              <span className="hint-touch">Fotoğraf çekebilir ya da galeriden seçebilirsin</span>
            </span>
            <span className="btn primary"><Icon name="image" />Görsel seç</span>
            <span className="drop-meta" id="drop-meta">JPG, PNG ya da WEBP · en fazla 20 MB · kaydedilmez</span>
          </label>
        </div>

        <figure className="demo" aria-label="Örnek: fotoğraftan okunup çözülmüş bir sudoku">
          <div className="panel">
            <div className="demo-caption">
              <h2>Örnek sonuç</h2>
              <span className="chip"><Icon name="check" />Tek çözüm doğrulandı</span>
            </div>
            <Board id="demo-board" board={DEMO} solution={DEMO_SOLUTION} corrected={DEMO_CORRECTED} decorative />
            <ul className="legend" aria-hidden="true">
              <li><span className="swatch given">5</span>Fotoğraftan okunan</li>
              <li><span className="swatch solved">4</span>Bulunan çözüm</li>
              <li><span className="swatch corrected">7</span>Kurallarla düzeltilen</li>
            </ul>
          </div>
        </figure>
      </div>

      <div className="features">
        {FEATURES.map(f => (
          <article className="feature" key={f.title}>
            <div className="feature-icon"><Icon name={f.icon} /></div>
            <h3>{f.title}</h3>
            <p>{f.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
