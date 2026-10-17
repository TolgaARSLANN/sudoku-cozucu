import type { CheckStatus, SolveStatus } from "../api";
import { Icon, type IconName } from "./Icon";

export type StatusKind = SolveStatus | CheckStatus | "bekle" | "hata";

export interface Status {
  kind: StatusKind;
  text: string;
}

const ICONS: Record<Exclude<StatusKind, "bekle">, IconName> = {
  cozuldu: "check", kontrol_edildi: "check", cozulemedi: "alert", izgara_yok: "alert", hata: "x",
};

/** Durum bildirimi: renk tek başına anlam taşımasın diye her durumun kendi simgesi var. */
export function StatusBanner({ status }: { status: Status | null }) {
  // Bölge her zaman sayfada durur ki ekran okuyucular içerik değişince duyursun
  return (
    <div id="status" role="status" aria-live="polite" className={status?.kind} hidden={!status}>
      {status && (
        <>
          {status.kind === "bekle" ? <span className="spinner" aria-hidden="true" /> : <Icon name={ICONS[status.kind]} />}
          <span>{status.text}</span>
        </>
      )}
    </div>
  );
}

export function LoadingSkeleton() {
  return (
    <section id="loading" className="result-grid" aria-hidden="true">
      <div className="panel"><div className="skeleton title" /><div className="skeleton photo" /></div>
      <div className="panel"><div className="skeleton title" /><div className="skeleton square" /></div>
    </section>
  );
}
