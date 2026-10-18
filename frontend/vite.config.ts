import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api is proxied to Django so the browser sees a single origin (no CORS noise).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_PROXY_TARGET ?? "http://localhost:8000" },
  },
});
