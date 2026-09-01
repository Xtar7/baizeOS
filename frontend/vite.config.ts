import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    proxy: {
      '/v1': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // 启动时序兜底：后端 5000 还没 listen 时，不要把 ECONNREFUSED 直接
        // 透回浏览器（对 SSE/聊天请求会变成永久失败）。改为 503 + Retry-After。
        configure(proxy, _options) {
          proxy.on('error', (err, _req, res) => {
            const r: any = res
            if (!r || r.writableEnded || r.headersSent) return
            if (err && (err as NodeJS.ErrnoException).code === 'ECONNREFUSED') {
              r.statusCode = 503
              r.setHeader('Retry-After', '1')
              r.setHeader('Content-Type', 'application/json')
              r.end(
                JSON.stringify({
                  error: 'backend_not_ready',
                  detail:
                    '后端尚未监听 5000，请稍后重试（start.py 已保证就绪再开浏览器）',
                }),
              )
            }
          })
        },
      },
    },
  },
})
