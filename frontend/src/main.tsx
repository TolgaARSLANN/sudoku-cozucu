import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// Yazı tipleri projeyle birlikte gelir: Google Fonts'a istek gitmez, ziyaretçinin IP'si paylaşılmaz.
// Sadece kullanılan kalınlıklar ve Türkçe harfleri kapsayan alt kümeler (latin + latin-ext).
import "@fontsource/outfit/latin-500.css";
import "@fontsource/outfit/latin-ext-500.css";
import "@fontsource/outfit/latin-600.css";
import "@fontsource/outfit/latin-ext-600.css";
import "@fontsource/outfit/latin-700.css";
import "@fontsource/outfit/latin-ext-700.css";
import "@fontsource/work-sans/latin-400.css";
import "@fontsource/work-sans/latin-ext-400.css";
import "@fontsource/work-sans/latin-500.css";
import "@fontsource/work-sans/latin-ext-500.css";
import "@fontsource/work-sans/latin-600.css";
import "@fontsource/work-sans/latin-ext-600.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
