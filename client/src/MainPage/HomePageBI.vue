<script setup>
import { ArrowRight, Pause, Play } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { version } from '../../package.json'
import BILogo from './components/BILogo.vue'
import OceanAquarium from './aquarium/OceanAquarium.vue'
import { sections } from './js/homeSections.js'
import { useHomeMotion } from './js/useHomeMotion.js'
import { useOceanTheme } from './js/useOceanTheme.js'

const { paused } = useHomeMotion()
const theme = useOceanTheme()
</script>

<template>
  <section class="ocean-page" :data-theme="theme" aria-labelledby="bi-ocean-title">
    <div class="ocean-scene" aria-hidden="true"><OceanAquarium :paused="paused" :theme="theme" /></div>
    <header class="ocean-top">
      <BILogo class="ocean-logo" :paused="paused" role="img" aria-label="ERGO MS BI" />
      <button class="ocean-motion" type="button" :aria-label="paused ? 'Включить анимацию' : 'Приостановить анимацию'"
              :title="paused ? 'Включить анимацию' : 'Приостановить анимацию'" @click="paused = !paused">
        <component :is="paused ? Play : Pause" :size="16" aria-hidden="true" />
      </button>
    </header>
    <div class="ocean-heading">
      <h1 id="bi-ocean-title" class="ocean-title">Океан данных</h1>
      <span class="ocean-release" lang="en">release {{ version }}</span>
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
