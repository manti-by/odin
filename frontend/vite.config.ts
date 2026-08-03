import { URL, fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  base: "/static/",
  plugins: [
    react(),
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      injectRegister: false,
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico", "favicon/*.png"],
      injectManifest: {
        manifestTransforms: [
          (entries) => {
            const transformed = entries.map((entry) => ({
              ...entry,
              url: `/static/${entry.url}`,
            }));
            return { manifest: transformed, warnings: [] };
          },
        ],
      },
      manifest: {
        name: "ODIN",
        short_name: "ODIN",
        description: "ODIN IoT Dashboard - Sensor Management, Weather Monitoring, and Home Automation",
        start_url: "/",
        display: "standalone",
        orientation: "portrait-primary",
        background_color: "#161614",
        theme_color: "#242b23",
        scope: "/",
        categories: ["utilities", "lifestyle"],
        icons: [
          { sizes: "16x16", src: "/static/favicon.ico", type: "image/x-icon" },
          { sizes: "32x32", src: "/static/favicon/32.png", type: "image/png" },
          { sizes: "72x72", src: "/static/favicon/72.png", type: "image/png" },
          { sizes: "96x96", src: "/static/favicon/96.png", type: "image/png" },
          { sizes: "128x128", src: "/static/favicon/128.png", type: "image/png" },
          { sizes: "144x144", src: "/static/favicon/144.png", type: "image/png" },
          { sizes: "152x152", src: "/static/favicon/152.png", type: "image/png" },
          { sizes: "192x192", src: "/static/favicon/192.png", type: "image/png" },
          { sizes: "384x384", src: "/static/favicon/384.png", type: "image/png" },
          { sizes: "512x512", src: "/static/favicon/512.png", type: "image/png" },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/admin": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/static": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
