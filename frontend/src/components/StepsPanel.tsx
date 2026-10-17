import type { Step } from "../api";
import { Icon } from "./Icon";

/** "Nasıl gördüm?": programın fotoğrafı adım adım nasıl işlediğini gösterir. */
export function StepsPanel({ steps, open }: { steps: Step[]; open: boolean }) {
  return (
    <details className="panel steps-panel" id="steps" open={open}>
      <summary>
        <span className="summary-icon"><Icon name="scan" /></span>
        <span>
          <strong>Nasıl gördüm?</strong>
          <span className="summary-hint">Fotoğrafın adım adım nasıl işlendiğini gör</span>
        </span>
      </summary>
      <ol className="steps">
        {steps.map((step, i) => (
          <li className="step" key={step.baslik}>
            <div className="step-head">
              <span className="step-num" aria-hidden="true">{i + 1}</span>
              <h3>{step.baslik}</h3>
            </div>
            <div className="step-image"><img src={step.gorsel} alt={step.baslik} loading="lazy" /></div>
            <p>{step.aciklama}</p>
          </li>
        ))}
      </ol>
    </details>
  );
}
