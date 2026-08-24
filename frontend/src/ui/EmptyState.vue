<script setup lang="ts">
import Icon from '@/ui/Icon.vue'

defineProps<{
  icon?: string
  title: string
  hint?: string
}>()
</script>

<template>
  <div class="empty">
    <div class="empty__mark" aria-hidden="true">
      <Icon :name="icon ?? 'spark'" :size="26" :stroke-width="1.3" />
    </div>
    <h3 class="empty__title">{{ title }}</h3>
    <p v-if="hint" class="empty__hint">{{ hint }}</p>
    <div v-if="$slots.default" class="empty__actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 48px 24px;
}

.empty__mark {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  border-radius: 20px;
  color: var(--accent-text);
  background: var(--accent-soft);
  margin-bottom: 18px;
}

.empty__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.empty__hint {
  margin-top: 6px;
  font-size: 13.5px;
  color: var(--ink-3);
  max-width: 40ch;
}

.empty__actions {
  margin-top: 18px;
}
</style>
