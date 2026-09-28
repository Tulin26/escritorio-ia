import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// "npm run dev" abre o painel em http://localhost:5173 e repassa /api para o server.js (porta 4321).
// "npm run build" gera painel/dist, que o server.js (PC) e o Vercel (online) servem.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:4321' } },
  build: { outDir: 'dist', emptyOutDir: true },
});
