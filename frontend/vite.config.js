import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5180 must be in the FastAPI CORS allow_origins list (venv/main.py)
export default defineConfig({
  plugins: [react()],
  server: { port: 5180, strictPort: true },
});
