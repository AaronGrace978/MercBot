import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  build: {
    sourcemap: false,
    minify: "esbuild",
    cssMinify: true,
    target: "es2022",
    reportCompressedSize: true,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-window"],
          "tauri-vendor": ["@tauri-apps/api"],
        },
      },
    },
  },
  esbuild: {
    drop: ["debugger"],
    legalComments: "none",
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
});
