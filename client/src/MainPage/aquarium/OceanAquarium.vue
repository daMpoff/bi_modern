<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createAquariumPainter, FRAMES_PER_SECOND, STILL_AT } from './painter'
import aquariumLicense from './LICENSE.txt?raw'

const props = defineProps({
  paused: Boolean,
  theme: { type: String, default: 'dark', validator: value => ['light', 'dark'].includes(value) }
})
const canvas = ref(null)
let dispose

onMounted(() => {
  const element = canvas.value
  const context = element.getContext('2d', { alpha: false })
  if (!context) return

  const painter = createAquariumPainter(element, context)
  let seconds = props.paused ? STILL_AT : 0
  let renderedTick = -1
  let previousTime = null
  let frameId = 0
  let onScreen = false

  function draw(force = false) {
    const tick = Math.floor(seconds * FRAMES_PER_SECOND + 1e-6)
    if (force || tick !== renderedTick) {
      painter.draw(seconds, props.theme)
      renderedTick = tick
    }
  }

  function advance(now) {
    if (previousTime !== null) seconds += (now - previousTime) / 1000
    previousTime = now
    draw()
    frameId = requestAnimationFrame(advance)
  }

  function updatePlayback() {
    if (onScreen && !document.hidden && !props.paused) {
      if (!frameId) frameId = requestAnimationFrame(advance)
    } else {
      cancelAnimationFrame(frameId)
      frameId = 0
      previousTime = null
    }
  }

  function resize() {
    if (painter.resize()) draw(true)
  }

  resize()
  const sizeObserver = new ResizeObserver(resize)
  sizeObserver.observe(element)
  const visibilityObserver = new IntersectionObserver(([entry]) => {
    onScreen = entry.isIntersecting
    updatePlayback()
  })
  visibilityObserver.observe(element)
  document.addEventListener('visibilitychange', updatePlayback)
  const stopWatching = watch(() => props.paused, updatePlayback, { flush: 'sync' })
  const stopWatchingTheme = watch(() => props.theme, () => draw(true))
  dispose = () => {
    stopWatching()
    stopWatchingTheme()
    cancelAnimationFrame(frameId)
    sizeObserver.disconnect()
    visibilityObserver.disconnect()
    document.removeEventListener('visibilitychange', updatePlayback)
  }
})

onBeforeUnmount(() => dispose?.())
</script>

<template>
  <canvas ref="canvas" class="ocean-aquarium" :data-theme="theme" :data-license="aquariumLicense" aria-hidden="true" />
</template>

<style scoped>
.ocean-aquarium {
  display: block;
  width: 100%;
  height: 100%;
  background: #061419;
  pointer-events: none;
}
.ocean-aquarium[data-theme='light'] {
  background: #f2f7f4;
}
</style>
