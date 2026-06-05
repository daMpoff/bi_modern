<script setup>
import { ref, onMounted, watch } from 'vue'
import { Plug, BarChart3, Database } from 'lucide-vue-next'
import { useRouter, useRoute } from 'vue-router'
import BILogo from '@/modules/bi_analysis_modern/client/src/MainPage/components/BILogo.vue'
import GraphCloudShader from '@/modules/bi_analysis_modern/client/src/MainPage/components/GraphCloudShader.vue'
import { useCardTilt } from './js/use-card-tilt.js'

const router = useRouter()
const route = useRoute()
const activeTab = ref(null)
const { handleMouseMove, handleMouseLeave, getTiltStyle } = useCardTilt(6)

const tabs = [
  {
    id: 'connections',
    name: 'Подключения',
    icon: Plug,
    route: '/bi-modern/connections',
    description: 'Работа с источниками данных, просмотр и выбор данных для дашбордов',
    colorClass: 'info'
  },
  {
    id: 'data',
    name: 'Данные',
    icon: Database,
    route: '/bi-modern/pipelines/',
    description: 'Создание пайплайнов обработки данных и графиков для дашбордов',
    colorClass: 'warning'
  },
  {
    id: 'graphs',
    name: 'Дашборды',
    icon: BarChart3,
    route: '/bi-modern/dashboard/',
    description: 'Создание дашбордов с визуальными блоками и графиками',
    colorClass: 'success'
  }
]

onMounted(() => updateActiveTab())
watch(() => route.path, () => updateActiveTab())

const handleTabClick = (tab) => {
  activeTab.value = tab.id
  if (tab.route) router.push(tab.route)
}

const updateActiveTab = () => {
  const currentPath = route.path
  const matched = tabs.find(tab => currentPath.startsWith(tab.route))
  activeTab.value = matched ? matched.id : null
}
</script>

<template>
  <div class="homepage-bi">
    <div class="background-shader">
      <GraphCloudShader />
    </div>

    <div class="content-wrapper">
      <div class="left-column">
        <BILogo class="bi-logo" />
      </div>

      <div class="right-column">
        <div
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab-item', `tab-item--${tab.colorClass}`, { active: activeTab === tab.id }]"
          :style="getTiltStyle(tab.id)"
          @click="handleTabClick(tab)"
          @mousemove="handleMouseMove($event, tab.id)"
          @mouseleave="handleMouseLeave(tab.id)"
        >
          <div class="tab-content">
            <div class="tab-icon-wrapper">
              <component :is="tab.icon" :size="26" class="tab-icon" />
            </div>
            <div class="tab-text-content">
              <h3 class="tab-title">{{ tab.name }}</h3>
              <p class="tab-description">{{ tab.description }}</p>
            </div>
            <div class="tab-arrow">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
          <div class="tab-gradient-border"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import './scss/home-page-bi.scss';
</style>
