import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, checkImage, solveBoard, solveImage, type CheckResult, type Photo } from "./api";
import { CheckView } from "./components/CheckView";
import { exampleUrl, Hero, type Example, type Task } from "./components/Hero";
import { DropOverlay, Footer, TopBar } from "./components/Layout";
import { ResultView, type ResultData } from "./components/ResultView";
import { LoadingSkeleton, StatusBanner, type Status } from "./components/StatusBanner";

type View = "hero" | "loading" | "result" | "check";

const errorText = (e: unknown) => (e instanceof ApiError ? e.message : "Beklenmeyen bir hata oluştu, tekrar dener misin?");

export default function App() {
  const [view, setView] = useState<View>("hero");
  const [status, setStatus] = useState<Status | null>(null);
  const [result, setResult] = useState<ResultData | null>(null);
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [task, setTask] = useState<Task>("coz");
  const taskRef = useRef<Task>("coz");  // pencere dinleyicilerinden de güncel değer okunabilsin
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const busyRef = useRef(false);  // pencere dinleyicilerinden de güncel değer okunabilsin
  const fileInput = useRef<HTMLInputElement>(null);
  const resultCount = useRef(0);
  const photo = useRef<Photo | null>(null);  // düzeltme sonrası çözümü çizmek için son fotoğraf
  const originalUrl = useRef<string | null>(null);  // ipucu modunda çözümsüz fotoğraf

  // Aynı anda tek istek: sürerken yeni yükleme ve tekrar tıklama yok sayılır
  const startBusy = (on: boolean) => {
    busyRef.current = on;
    setBusy(on);
  };

  const changeTask = (t: Task) => {
    taskRef.current = t;
    setTask(t);
  };

  const handleFile = useCallback(async (file: File | null | undefined) => {
    if (busyRef.current) return;
    if (!file || !file.type.startsWith("image/")) {
      setStatus({ kind: "hata", text: "Bu bir görsel dosyası değil. JPG, PNG ya da WEBP bir görsel seç." });
      return;
    }
    startBusy(true);
    const checking = taskRef.current === "kontrol";
    setStatus({ kind: "bekle", text: checking ? "Rakamlar okunuyor, el yazın kontrol ediliyor…"
                                              : "Izgara aranıyor, rakamlar okunuyor…" });
    setView("loading");
    window.scrollTo({ top: 0 });
    try {
      if (checking) {
        const data = await checkImage(file);
        setStatus({ kind: data.durum, text: data.mesaj });
        setCheck(data);
        setView("check");
        return;
      }
      const data = await solveImage(file);
      photo.current = data.koseler && { file, corners: data.koseler };
      if (originalUrl.current) URL.revokeObjectURL(originalUrl.current);
      originalUrl.current = URL.createObjectURL(file);
      setStatus({ kind: data.durum, text: data.mesaj });
      setResult({
        id: ++resultCount.current,
        image: data.gorsel,
        original: originalUrl.current,
        difficulty: data.zorluk,
        hints: data.ipuclari,
        board: data.tahta,
        solution: data.cozum,
        corrected: data.duzeltilen,
        unsure: data.emin_degil,
        warnings: data.uyarilar,
        steps: data.adimlar,
      });
      setView("result");
    } catch (e) {
      setStatus({ kind: "hata", text: errorText(e) });
      setView("hero");
    } finally {
      startBusy(false);
    }
  }, []);

  const handleFix = useCallback(async (board: number[]) => {
    if (busyRef.current) return;
    startBusy(true);
    setStatus({ kind: "bekle", text: "Çözülüyor…" });
    try {
      const data = await solveBoard(board, photo.current);
      setStatus({ kind: data.durum, text: data.mesaj });
      if (data.cozum) {
        setResult(r => r && {
          ...r, board, solution: data.cozum, corrected: [], unsure: [], image: data.gorsel ?? r.image,
          difficulty: data.zorluk, hints: data.ipuclari,
        });
      }
    } catch (e) {
      setStatus({ kind: "hata", text: errorText(e) });
    } finally {
      startBusy(false);
    }
  }, []);

  // Örnek görsel sunucudan alınır ve kullanıcının yüklediği bir dosya gibi işlenir
  const handleExample = async (example: Example) => {
    if (busyRef.current) return;
    changeTask(example.task);
    try {
      const res = await fetch(exampleUrl(example.file));
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      handleFile(new File([blob], `${example.file}.jpg`, { type: "image/jpeg" }));
    } catch {
      setStatus({ kind: "hata", text: "Örnek görsel yüklenemedi. Sayfayı yenileyip tekrar dener misin?" });
    }
  };

  const openPicker = () => fileInput.current?.click();

  // Ekran görüntüsü Ctrl+V ile yapıştırılabilir
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const item = [...(e.clipboardData?.items ?? [])].find(i => i.type.startsWith("image/"));
      if (item) handleFile(item.getAsFile());
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleFile]);

  // Görsel pencerenin herhangi bir yerine bırakılabilir
  useEffect(() => {
    let depth = 0;  // iç içe öğelerde dragenter/dragleave çiftlerini saymak için
    const hasFiles = (e: DragEvent) => [...(e.dataTransfer?.types ?? [])].includes("Files");
    const onEnter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth++;
      setDragging(true);
    };
    const onOver = (e: DragEvent) => { if (hasFiles(e)) e.preventDefault(); };
    const onLeave = () => {
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDragging(false);
    };
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      depth = 0;
      setDragging(false);
      handleFile(e.dataTransfer?.files[0]);
    };
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragover", onOver);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, [handleFile]);

  return (
    <>
      <a className="skip" href="#main">İçeriğe geç</a>
      <TopBar />
      <main id="main" tabIndex={-1}>
        <div className="wrap">
          <StatusBanner status={status} />
          {view === "hero" && <Hero onPick={openPicker} busy={busy} task={task} onTaskChange={changeTask} onExample={handleExample} />}
          {view === "loading" && <LoadingSkeleton />}
          {view === "result" && result && (
            <ResultView key={result.id} result={result} busy={busy} onNewImage={openPicker} onFix={handleFix} />
          )}
          {view === "check" && check && <CheckView data={check} busy={busy} onNewImage={openPicker} />}
        </div>
      </main>
      <Footer />
      <input
        id="file"
        ref={fileInput}
        type="file"
        accept="image/*"
        hidden
        onChange={e => {
          handleFile(e.target.files?.[0]);
          e.target.value = "";  // aynı dosya tekrar seçilebilsin
        }}
      />
      {dragging && <DropOverlay />}
    </>
  );
}
