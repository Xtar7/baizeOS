<script setup lang="ts">
import ToastHost from '@/ui/ToastHost.vue'
import ConfirmHost from '@/ui/ConfirmHost.vue'
</script>

<template>
  <RouterView />
  <ToastHost />
  <ConfirmHost />
</template>
