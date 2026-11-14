import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/auth': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      // Solo la API JSON de contratos va al backend; las rutas React /contratos
      // (lista, formulario y detalle) las resuelve el SPA con fallback de Vite.
      '/contratos/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/pagos/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/api': 'http://localhost:5000'
    }
  }
})
