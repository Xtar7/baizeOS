<script setup lang="ts">
import { NConfigProvider, zhCN } from 'naive-ui'

const themeOverrides = {
  common: {
    primaryColor: '#0071e3',
    primaryColorHover: '#0077ED',
    primaryColorPressed: '#005bb5',
    textColorBase: 'var(--text-primary)',
    textColor1: 'var(--text-primary)',
    textColor2: 'var(--text-secondary)',
    borderColor: 'var(--border)',
    borderRadius: '8px',
    cardColor: 'var(--bg-elevated)',
    hoverColor: 'var(--bg-tertiary)',
    bodyColor: 'var(--bg-primary)',
  },
}
</script>

<template>
  <NConfigProvider
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="null"
  >
    <RouterView />
  </NConfigProvider>
</template>
