// vite.config.ts
import { defineConfig } from "vite";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { version } from "./package.json";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");

  return {
    define: {
      __APP_VERSION__: JSON.stringify(version),
    },
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/api": {
          target: env.VITE_API_PROXY_TARGET || "http://localhost:5001",
          changeOrigin: true,
        },
      },
    },
  };
});
