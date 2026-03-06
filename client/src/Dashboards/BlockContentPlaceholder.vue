<template>
  <div class="block-content-placeholder">
    {{ block?.type || 'Блок' }}
  </div>
</template>

<script setup>
defineProps({
  block: {
    type: Object,
    default: null
  }
})
</script>

<style scoped lang="scss">
.block-content-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 80px;
  color: var(--color-text-secondary, #666);
  font-size: 14px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
}
</style>
