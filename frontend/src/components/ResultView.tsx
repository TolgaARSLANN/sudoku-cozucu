import { useState } from "react";
import type { Correction, Step } from "../api";
import { Board } from "./Board";
import { Icon } from "./Icon";
import { StepsPanel } from "./StepsPanel";

export interface ResultData {
  id: number;                 // her yeni görselde değişir; düzeltme alanını sıfırlamak için
  image: string;
  board: number[] | null;
  solution: number[] | null;
  corrected: Correction[];
  unsure: number[];
  warnings: string[];
  steps: Step[];
}

interface ResultViewProps {
  result: ResultData;
  busy: boolean;
  onNewImage: () => void;
  onFix: (board: number[]) => void;
}

const cellName = (i: number) => `${Math.floor(i / 9) + 1}. satır ${(i % 9) + 1}. sütun`;

export function ResultView({ result, busy, onNewImage, onFix }: ResultViewProps) {
  const { board, solution, corrected } = result;
  return (
    <section id="result" aria-labelledby="result-title">
      <div className="toolbar">
        <div>
          <h1 id="result-title">Sonuç</h1>
          {board && (
            <div className="stats" id="stats">
              <span className="chip"><Icon name="grid" /><b>{board.filter(Boolean).length}</b> rakam okundu</span>
              {corrected.length > 0 && (
                <span className="chip"><Icon name="pencil" /><b>{corrected.length}</b> düzeltme</span>
              )}
              {solution && <span className="chip"><Icon name="shield" />Tek çözüm doğrulandı</span>}
            </div>
          )}
        </div>
        <div className="actions">
          <button className="btn" type="button" id="new-image" onClick={onNewImage} disabled={busy}>
            <Icon name="upload" />Yeni görsel
          </button>
          {/* Ekranda tek birincil eylem: çözüldüyse indir, çözülmediyse düzelt */}
          <a id="download" className={solution ? "btn primary" : "btn"} href={result.image} download="sudoku_cozum.jpg">
            <Icon name="download" />Görseli indir
          </a>
        </div>
      </div>

      {result.warnings.length > 0 && (
        <div className="tips" id="tips">
          <Icon name="alert" />
          <div>
            <strong>Fotoğrafı iyileştirmek için</strong>
            <ul>{result.warnings.map(w => <li key={w}>{w}</li>)}</ul>
          </div>
        </div>
      )}

      <div className="result-grid">
        <div className="panel">
          <div className="panel-head"><h2>Fotoğraf</h2></div>
          <div className="photo-frame"><img id="photo" src={result.image} alt="Çözümün üzerine çizildiği fotoğraf" /></div>
        </div>
        {board && <BoardPanel key={result.id} result={{ ...result, board }} busy={busy} onFix={onFix} />}
      </div>
      {/* Izgara bulunamadıysa sebebi burada görülür, o yüzden açık gelir */}
      {result.steps.length > 0 && <StepsPanel key={result.id} steps={result.steps} open={!board} />}
    </section>
  );
}

interface BoardPanelProps {
  result: ResultData & { board: number[] };
  busy: boolean;
  onFix: (board: number[]) => void;
}

function BoardPanel({ result, busy, onFix }: BoardPanelProps) {
  const { board, solution, corrected, unsure } = result;
  // Düzeltme modunda kullanıcının yazdığı rakamlar
  const [values, setValues] = useState(() => board.map(v => (v ? String(v) : "")));

  return (
    <div className="panel" id="board-panel">
      <div className="panel-head"><h2 id="board-title">{solution ? "Çözüm" : "Okunan rakamlar"}</h2></div>
      <Board
        id="board"
        board={board}
        solution={solution}
        corrected={corrected}
        unsure={unsure}
        values={values}
        onChange={(i, v) => setValues(prev => prev.map((old, j) => (j === i ? v : old)))}
        animate
      />

      <ul className="legend" id="legend">
        <li><span className="swatch given" aria-hidden="true">5</span>Fotoğraftan okunan</li>
        {solution && <li><span className="swatch solved" aria-hidden="true">4</span>Bulunan çözüm</li>}
        {solution && corrected.length > 0 && (
          <li><span className="swatch corrected" aria-hidden="true">7</span>Kurallarla düzeltilen</li>
        )}
        {!solution && unsure.length > 0 && (
          <li><span className="swatch unsure" aria-hidden="true" />Emin olunamayan</li>
        )}
      </ul>

      {!solution && (
        <p className="note" id="note">
          Eksik ya da yanlış okunan rakamları fotoğrafa bakarak düzeltebilirsin.
          {unsure.length > 0 && " Önce kesik çerçeveli hücrelere bak."}
          <span className="hint-desktop"> Hücreler arasında ok tuşlarıyla gezebilirsin.</span>
        </p>
      )}

      {/* Düzeltmeler sadece fareyle görülen ipucunda kalmasın: listede de yazsın */}
      {solution && corrected.length > 0 && (
        <div className="fixes" id="fixes">
          <strong>Kurallarla düzeltilen rakamlar</strong>
          <ul>
            {corrected.map(c => (
              <li key={c.hucre}>{cellName(c.hucre)}: {c.okunan} okundu, {board[c.hucre]} olmalı</li>
            ))}
          </ul>
        </div>
      )}

      {!solution && (
        <div className="actions">
          <button id="fix" className="btn primary" type="button" disabled={busy}
                  onClick={() => onFix(values.map(v => Number(v) || 0))}>
            <Icon name="check" />Düzelttim, tekrar çöz
          </button>
        </div>
      )}
    </div>
  );
}
