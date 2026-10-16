import { defineConfig } from 'vite';
export default defineConfig({ server: { proxy: { '/api': 'http://127.0.0.1:8017' } }, build: { rollupOptions: { output: { manualChunks: { graph: ['cytoscape'], react: ['react', 'react-dom'] } } } } });
