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
  gorsel: string;            // çözüm çizilmiş görsel (data URL)
}

export interface BoardResult {
  durum: "cozuldu" | "cozulemedi";
  mesaj: string;
  cozum: number[] | null;
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

export function solveBoard(tahta: number[]): Promise<BoardResult> {
  return request<BoardResult>("/api/coz-tahta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tahta }),
  });
}
