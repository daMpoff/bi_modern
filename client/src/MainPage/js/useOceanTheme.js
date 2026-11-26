import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const storageKey = 'bi-modern.ocean.theme'
const preferred = ref(null)
const validTheme = value => value === 'dark' || value === 'light'

export function useOceanTheme() {
  const system = window.matchMedia('(prefers-color-scheme: dark)')
  const inherited = ref('dark')

  function readHostTheme() {
    const value = document.documentElement.getAttribute('data-bs-theme')
    inherited.value = validTheme(value) ? value : system.matches ? 'dark' : 'light'
  }

  function selectTheme(value) {
    if (!validTheme(value)) return
    preferred.value = value
    try {
      window.localStorage.setItem(storageKey, value)
    } catch {
      // The embedded preview can restrict storage; keep the choice for this session.
    }
  }

  readHostTheme()
  try {
    const saved = window.localStorage.getItem(storageKey)
    if (validTheme(saved)) preferred.value = saved
  } catch {
    // Keep the current session preference.
  }

  const observer = new MutationObserver(readHostTheme)
  onMounted(() => {
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] })
    system.addEventListener('change', readHostTheme)
  })
  onBeforeUnmount(() => {
    observer.disconnect()
    system.removeEventListener('change', readHostTheme)
  })

  return { theme: computed(() => preferred.value ?? inherited.value), selectTheme }
}
