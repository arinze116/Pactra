import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const devProxyTarget = process.env.PACTRA_DEV_PROXY_TARGET?.trim()
  || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1_300,
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: devProxyTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
});
