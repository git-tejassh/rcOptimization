import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Static build: all data comes from /data/*.json (produced by `make export`).
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { chunkSizeWarningLimit: 4000 },
});
