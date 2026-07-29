import react from '@astrojs/react';
import { defineConfig } from 'astro/config';

export default defineConfig({
  integrations: [react()],
  output: 'static',
  vite: {
    server: {
      proxy: {
        '/api': 'http://127.0.0.1:8000',
        '/health': 'http://127.0.0.1:8000',
      },
    },
  },
});
