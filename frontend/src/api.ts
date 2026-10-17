// Flask sunucusunun (app.py) döndürdüğü veriler

export type SolveStatus = "cozuldu" | "cozulemedi" | "izgara_yok";

export interface Correction {
  hucre: number;   // 0-80 arası hücre indeksi
  okunan: number;  // fotoğraftan ilk okunan rakam
}

export interface ImageResult {
  durum: SolveStatus;
  mesaj: string;
  tahta: number[] | null;    // okunan rakamlar, boş = 0; ızgara bulunamazsa null
  cozum: number[] | null;
  duzeltilen: Correction[];
  emin_degil: number[];
  koseler: number[][] | null; // ızgaranın fotoğraftaki 4 köşesi; düzeltme sonrası çizim için geri gönderilir
  gorsel: string;            // çözüm çizilmiş görsel (data URL)
}

export interface BoardResult {
  durum: "cozuldu" | "cozulemedi";
  mesaj: string;
  cozum: number[] | null;
  gorsel: string | null;     // fotoğraf gönderildiyse çözüm çizilmiş hali
}

/** Düzeltme sonrası çözümün çizileceği asıl fotoğraf ve ızgaranın köşeleri. */
export interface Photo {
  file: File;
  corners: number[][];
}

/** Kullanıcıya gösterilecek mesajı taşıyan hata. */
export class ApiError extends Error {}

async function request<T>(url: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError("Sunucuya ulaşılamadı. app.py çalışıyor mu? Çalışıyorsa sayfayı yenileyip tekrar dene.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.hata ?? "Bir şeyler ters gitti, tekrar dener misin?");
  return data as T;
}

export function solveImage(file: File): Promise<ImageResult> {
  const form = new FormData();
  form.append("gorsel", file);
  return request<ImageResult>("/api/coz", { method: "POST", body: form });
}

export function solveBoard(tahta: number[], photo: Photo | null): Promise<BoardResult> {
  const form = new FormData();
  form.append("tahta", JSON.stringify(tahta));
  if (photo) {
    form.append("gorsel", photo.file);
    form.append("koseler", JSON.stringify(photo.corners));
  }
  return request<BoardResult>("/api/coz-tahta", { method: "POST", body: form });
}
