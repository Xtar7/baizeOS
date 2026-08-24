<script setup lang="ts">
import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import AppButton from '@/ui/AppButton.vue'
import AppModal from '@/ui/AppModal.vue'

const store = useSettingsStore()
const state = computed(() => store.confirmState)
</script>

<template>
  <AppModal
    :open="state.open"
    :title="state.title"
    :width="400"
    @update:open="(v) => !v && store.settleConfirm(false)"
  >
    <p v-if="state.body" class="confirm-body">{{ state.body }}</p>
    <template #footer>
      <AppButton variant="ghost" size="md" @click="store.settleConfirm(false)">
        {{ state.cancelText }}
      </AppButton>
      <AppButton
        :variant="state.danger ? 'danger' : 'solid'"
        size="md"
        @click="store.settleConfirm(true)"
      >
        {{ state.confirmText }}
      </AppButton>
    </template>
  </AppModal>
</template>

<style scoped>
.confirm-body {
  font-size: 13.5px;
  color: var(--ink-2);
  line-height: 1.65;
}
</style>
