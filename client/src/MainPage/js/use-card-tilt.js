import { ref, onUnmounted } from 'vue'

/**
 * Composable for 3D perspective tilt effect on card hover.
 * Returns refs and event handlers to bind to card elements.
 */
export function useCardTilt(maxAngle = 8) {
  const tiltStyles = ref({})

  function handleMouseMove(e, cardId) {
    const el = e.currentTarget
    if (!el) return

    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height

    const rotateY = (x - 0.5) * maxAngle * 2
    const rotateX = (0.5 - y) * maxAngle * 2

    tiltStyles.value[cardId] = {
      transform: `perspective(800px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.02, 1.02, 1.02)`,
      transition: 'transform 0.1s ease-out'
    }
  }

  function handleMouseLeave(cardId) {
    tiltStyles.value[cardId] = {
      transform: 'perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)',
      transition: 'transform 0.4s ease-out'
    }
  }

  function getTiltStyle(cardId) {
    return tiltStyles.value[cardId] || {
      transform: 'perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)',
      transition: 'transform 0.4s ease-out'
    }
  }

  onUnmounted(() => {
    tiltStyles.value = {}
  })

  return {
    tiltStyles,
    handleMouseMove,
    handleMouseLeave,
    getTiltStyle
  }
}
