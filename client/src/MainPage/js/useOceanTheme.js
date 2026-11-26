import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useOceanTheme() {
  const system = window.matchMedia('(prefers-color-scheme: dark)')
  const root = document.documentElement

  function readHostTheme() {
    const mode = root.getAttribute('data-bs-theme')
    if (mode === 'light' || mode === 'dark') return mode
    return system.matches ? 'dark' : 'light'
  }

  const theme = ref(readHostTheme())
  function syncTheme() {
    theme.value = readHostTheme()
  }

  const observer = new MutationObserver(syncTheme)
  onMounted(() => {
    observer.observe(root, { attributes: true, attributeFilter: ['data-bs-theme'] })
    system.addEventListener('change', syncTheme)
    syncTheme()
  })
  onBeforeUnmount(() => {
    observer.disconnect()
    system.removeEventListener('change', syncTheme)
  })

  return theme
}
