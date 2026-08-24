import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './style/tokens.css'
import './style/base.css'
import './style/markdown.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
