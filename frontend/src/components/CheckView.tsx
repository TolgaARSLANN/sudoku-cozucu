import type { CheckResult, Verdict } from "../api";
import { Board } from "./Board";
import { Icon } from "./Icon";
import { cellName } from "./ResultView";

interface CheckViewProps {
  data: CheckResult;
  busy: boolean;
  onNewImage: () => void;
}

/** Kalemle doldurulmuş sudokunun kontrol sonucu: hangi el yazısı rakam doğru, hangisi yanlış. */
export function CheckView({ data, busy, onNewImage }: CheckViewProps) {
  const { ozet, cozum } = data;
  const printed = new Array<number>(81).fill(0);
  const written = new Array<number>(81).fill(0);
  const marks: Partial<Record<number, Verdict>> = {};
  for (const r of data.sonuclar) {
    if (r.durum === "basili") {
      printed[r.hucre] = r.okunan;
    } else {
      written[r.hucre] = r.okunan;
      marks[r.hucre] = r.durum;
    }
  }
  const wrong = data.sonuclar.filter(r => r.durum === "yanlis");
  const unsure = data.sonuclar.filter(r => r.durum === "kontrol");

  return (
    <section id="result" aria-labelledby="result-title">
      <div className="toolbar">
        <div>
          <h1 id="result-title">Kontrol sonucu</h1>
          {ozet && (
            <div className="stats" id="stats">
              <span className="chip"><Icon name="check" /><b>{ozet.dogru}</b> doğru</span>
              <span className="chip"><Icon name="x" /><b>{ozet.yanlis}</b> yanlış</span>
              {ozet.kontrol > 0 && <span className="chip"><Icon name="alert" /><b>{ozet.kontrol}</b> kontrol et</span>}
              <span className="chip"><Icon name="grid" /><b>{ozet.bos}</b> boş</span>
            </div>
          )}
        </div>
        <div className="actions">
          <button className="btn" type="button" id="new-image" onClick={onNewImage} disabled={busy}>
            <Icon name="upload" />Yeni görsel
          </button>
          <a id="download" className="btn primary" href={data.gorsel} download="sudoku_kontrol.jpg">
            <Icon name="download" />Görseli indir
          </a>
        </div>
      </div>

      <div className="result-grid">
        <div className="panel">
          <div className="panel-head"><h2>Fotoğraf</h2></div>
          <div className="photo-frame">
            <img id="photo" src={data.gorsel} alt="Yanlış rakamları işaretlenmiş fotoğraf" />
          </div>
        </div>
        {cozum && ozet && (
          <div className="panel" id="board-panel">
            <div className="panel-head"><h2 id="board-title">Senin çözümün</h2></div>
            <Board id="board" board={printed} solution={written} marks={marks} animate />
            <ul className="legend" id="legend">
              <li><span className="swatch given" aria-hidden="true">5</span>Basılı</li>
              <li><span className="swatch solved" aria-hidden="true">4</span>Doğru</li>
              <li><span className="swatch wrong" aria-hidden="true">7</span>Yanlış</li>
              {unsure.length > 0 && <li><span className="swatch unsure" aria-hidden="true">2</span>Kontrol et</li>}
            </ul>

            {wrong.length > 0 && (
              <div className="mistakes" id="mistakes">
                <strong>Yanlış yazılanlar</strong>
                <ul>{wrong.map(r => <li key={r.hucre}>{cellName(r.hucre)}: {r.okunan} yazılmış</li>)}</ul>
                {/* Doğru cevap hemen söylenmez: önce kendisi bulmak isteyebilir */}
                <details id="answers">
                  <summary>Doğrularını göster</summary>
                  <ul>{wrong.map(r => <li key={r.hucre}>{cellName(r.hucre)}: {cozum[r.hucre]} olmalı</li>)}</ul>
                </details>
              </div>
            )}
            {unsure.length > 0 && (
              <div className="fixes" id="unsure-list">
                <strong>Emin olamadıklarım</strong>
                <ul>{unsure.map(r => <li key={r.hucre}>{cellName(r.hucre)}: {r.okunan} gibi okudum ama emin değilim</li>)}</ul>
              </div>
            )}
            {wrong.length === 0 && unsure.length === 0 && (
              <p className="note" id="note">
                {ozet.bos === 0 ? "Tebrikler, bulmacayı hatasız tamamlamışsın!" : "Şu ana kadar yazdıkların doğru, devam!"}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
