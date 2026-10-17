import { Icon } from "./Icon";

export function TopBar() {
  return (
    <header className="topbar">
      <div className="wrap">
        <a className="brand" href="/" aria-label="Sudoku Çözücü, ana sayfa">
          <span className="brand-mark"><Icon name="grid" /></span>
          Sudoku Çözücü
        </a>
        {/* Telefonda sadece kilit simgesi görünür; açıklama yine de okunabilsin */}
        <span className="badge" title="Fotoğrafın kaydedilmez">
          <Icon name="lock" />
          <span className="badge-text">Fotoğrafın kaydedilmez</span>
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
        Yüklediğin fotoğraf sadece sonucu hazırlamak için sunucunun belleğinde işlenir; diske kaydedilmez,
        saklanmaz ve kimseyle paylaşılmaz.
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
