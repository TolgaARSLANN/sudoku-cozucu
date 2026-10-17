import { useEffect, useState } from "react";
import { Icon } from "./Icon";

/** Telefonun paylaşım menüsü (WhatsApp, mesaj...): sadece tarayıcı dosya paylaşmayı destekliyorsa görünür. */
export function ShareButton({ image, name }: { image: string; name: string }) {
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(image)  // data URL → dosya
      .then(r => r.blob())
      .then(blob => {
        const f = new File([blob], name, { type: "image/jpeg" });
        if (alive && navigator.canShare?.({ files: [f] })) setFile(f);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [image, name]);

  if (!file) return null;
  return (
    <button className="btn" type="button" id="share"
            onClick={() => navigator.share({ files: [file] }).catch(() => {})}>  {/* vazgeçmek hata değil */}
      <Icon name="share" />Paylaş
    </button>
  );
}
