<script setup>
import { ArrowRight, Moon, Pause, Play, Sun } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import BILogo from './components/BILogo.vue'
import OceanAquarium from './aquarium/OceanAquarium.vue'
import { sections } from './js/homeSections.js'
import { useHomeMotion } from './js/useHomeMotion.js'
import { useOceanTheme } from './js/useOceanTheme.js'

const { paused } = useHomeMotion()
const { theme, selectTheme } = useOceanTheme()
const themes = [
  { value: 'light', label: 'Светлая', icon: Sun },
  { value: 'dark', label: 'Тёмная', icon: Moon }
]
</script>

<template>
  <section class="ocean-page" :data-theme="theme" aria-labelledby="bi-ocean-title">
    <div class="ocean-scene" aria-hidden="true"><OceanAquarium :paused="paused" :theme="theme" /></div>
    <header class="ocean-top">
      <BILogo class="ocean-logo" :paused="paused" role="img" aria-label="ERGO MS BI" />
      <div class="ocean-tools">
        <div class="ocean-themes" role="group" aria-label="Цветовая тема">
          <button v-for="option in themes" :key="option.value" type="button"
                  :aria-pressed="theme === option.value" @click="selectTheme(option.value)">
            <component :is="option.icon" :size="15" aria-hidden="true" /> {{ option.label }}
          </button>
        </div>
        <button class="ocean-motion" type="button" :aria-label="paused ? 'Включить анимацию' : 'Приостановить анимацию'"
                :title="paused ? 'Включить анимацию' : 'Приостановить анимацию'" @click="paused = !paused">
          <component :is="paused ? Play : Pause" :size="16" />
        </button>
      </div>
    </header>
    <div class="ocean-heading">
      <h1 id="bi-ocean-title" class="ocean-title">Океан данных</h1>
      <span class="ocean-release" lang="en">release 0.3.0</span>
    </div>
    <nav class="ocean-sections" aria-label="Разделы BI">
      <RouterLink v-for="section in sections" :key="section.to" class="ocean-card" :to="section.to">
        <span class="section-icon"><component :is="section.icon" :size="22" :stroke-width="1.7" aria-hidden="true" /></span>
        <span class="section-label"><strong>{{ section.name }}</strong><small>{{ section.description }}</small></span>
        <ArrowRight class="section-arrow" :size="18" aria-hidden="true" />
      </RouterLink>
    </nav>
  </section>
</template>

<style scoped src="./scss/home-page-bi.scss" lang="scss"></style>
