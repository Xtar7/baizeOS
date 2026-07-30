import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import AutoImport from 'unplugin-auto-import/vite'
import IconsResolver from 'unplugin-icons/resolver'
import Icons from 'unplugin-icons/vite'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [
        IconsResolver({ prefix: 'Icon' }),
        NaiveUiResolver(),
      ],
    }),
    Components({
      resolvers: [
        IconsResolver({ enabledCollections: ['ionicons5'] }),
        NaiveUiResolver(),
      ],
    }),
    Icons({ autoInstall: true }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/v1': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
