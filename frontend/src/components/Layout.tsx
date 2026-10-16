import { Icon } from "./Icon";

export function TopBar() {
  return (
    <header className="topbar">
      <div className="wrap">
        <a className="brand" href="/" aria-label="Sudoku Çözücü, ana sayfa">
          <span className="brand-mark"><Icon name="grid" /></span>
          Sudoku Çözücü
        </a>
        <span className="badge">
          <Icon name="lock" />
          <span className="badge-text">Görseller bu bilgisayarda işlenir</span>
        </span>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer>
      <div className="wrap">
        <Icon name="lock" />
        Yüklediğin görseller bu bilgisayarda çalışan sunucuda işlenir, başka bir yere gönderilmez.
      </div>
    </footer>
  );
}

export function DropOverlay() {
  return (
    <div id="drop-overlay" aria-hidden="true">
      <div className="overlay-card"><Icon name="upload" />Bırak, çözelim</div>
    </div>
  );
}
