import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// Static build. `dist/index.html` is one self-contained file (JS + CSS inlined) that also works when double-clicked
// (file://): the results are loaded from the classic script data/bundle.js written by `rcopt export`.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  base: "./",
  build: { chunkSizeWarningLimit: 6000 },
});
