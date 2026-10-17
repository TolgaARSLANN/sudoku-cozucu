import { useRef, type CSSProperties, type KeyboardEvent } from "react";
import type { Correction } from "../api";

interface BoardProps {
  board: number[];                 // fotoğraftan okunan rakamlar, boş = 0
  solution: number[] | null;       // çözüm yoksa tahta düzenlenebilir olur
  corrected?: Correction[];
  unsure?: number[];
  values?: string[];               // düzenleme modunda hücre değerleri
  onChange?: (index: number, value: string) => void;
  animate?: boolean;               // çözülen rakamlar sırayla belirsin
  highlight?: number[];            // ipucu modunda gerekçeye konu olan hücreler
  focus?: number;                  // ipucu modunda rakamın yerleştiği hücre
  id?: string;
  decorative?: boolean;            // giriş ekranındaki örnek: ekran okuyuculardan gizli
}

const ARROW_STEPS: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -9, ArrowDown: 9 };

export function Board({
  board, solution, corrected = [], unsure = [], values, onChange, animate = false, highlight = [], focus, id,
  decorative = false,
}: BoardProps) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const fixedFrom = new Map(corrected.map(c => [c.hucre, c.okunan]));
  let order = 0;

  // Düzeltme modunda ok tuşlarıyla hücreler arası gezinme
  function handleKey(i: number, e: KeyboardEvent<HTMLInputElement>) {
    const step = ARROW_STEPS[e.key];
    const next = step && inputs.current[i + step];
    if (next) {
      e.preventDefault();
      next.focus();
    }
  }

  const cells = Array.from({ length: 81 }, (_, i) => {
    const r = Math.floor(i / 9), c = i % 9;
    const classes = ["cell"];
    if (c === 2 || c === 5) classes.push("box-r");
    if (r === 2 || r === 5) classes.push("box-b");
    if (c === 8) classes.push("c9");
    if (r === 8) classes.push("r9");
    if (highlight.includes(i)) classes.push("hl");
    if (focus === i) classes.push("focus");

    if (!solution && values && onChange) {
      if (unsure.includes(i)) classes.push("unsure");
      return (
        <div key={i} className={classes.join(" ")}>
          <input
            ref={el => { inputs.current[i] = el; }}
            value={values[i]}
            inputMode="numeric"
            maxLength={1}
            autoComplete="off"
            aria-label={`Satır ${r + 1}, sütun ${c + 1}`}
            onChange={e => onChange(i, e.target.value.replace(/[^1-9]/g, ""))}
            onFocus={e => e.target.select()}
            onKeyDown={e => handleKey(i, e)}
          />
        </div>
      );
    }

    const old = fixedFrom.get(i);
    if (old !== undefined) {
      classes.push("corrected");
      return (
        <div key={i} className={classes.join(" ")} title={`${old} olarak okundu, sudoku kurallarına göre ${board[i]} olmalı`}>
          {board[i]}
        </div>
      );
    }
    if (board[i]) {
      classes.push("given");
      return <div key={i} className={classes.join(" ")}>{board[i]}</div>;
    }
    if (!solution?.[i]) return <div key={i} className={classes.join(" ")} />;  // ipucu modunda henüz açılmamış
    classes.push("solved");
    return (
      <div key={i} className={classes.join(" ")} style={{ "--d": order++ } as CSSProperties}>
        {solution[i]}
      </div>
    );
  });

  return (
    <div id={id} className={animate ? "board animate" : "board"} aria-hidden={decorative || undefined}>
      {cells}
    </div>
  );
}
