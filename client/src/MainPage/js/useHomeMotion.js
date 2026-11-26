import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useHomeMotion() {
  const preference = typeof window === 'undefined' ? null : window.matchMedia('(prefers-reduced-motion: reduce)')
  const paused = ref(preference?.matches ?? false)
  function syncPreference() { paused.value = preference.matches }
  onMounted(() => preference?.addEventListener('change', syncPreference))
  onBeforeUnmount(() => preference?.removeEventListener('change', syncPreference))
  return { paused }
}
