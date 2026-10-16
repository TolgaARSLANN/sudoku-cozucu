import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Derleme çıktısı Flask'ın sunduğu static/ klasörüne gider; dosyalar /static/ altından yüklenir.
// Geliştirmede (npm run dev) /api istekleri çalışan Flask sunucusuna yönlendirilir.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/static/" : "/",
  build: { outDir: "../static", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:5000" } },
}));
