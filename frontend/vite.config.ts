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
    // 端口被占用时直接报错而不是静默换到 3001 —— start.py 启动前已检查过
    // 3000，端口冲突必须显式暴露，否则浏览器打开的地址和实际服务的地址
    // 对不上，表现为"前端连不上后端"。
    strictPort: true,
    proxy: {
      '/v1': {
        // 用 127.0.0.1 而非 localhost：Windows 上 localhost 可能先解析到
        // ::1，而后端只监听 0.0.0.0（IPv4），会偶发 ECONNREFUSED。
        target: 'http://127.0.0.1:5000',
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