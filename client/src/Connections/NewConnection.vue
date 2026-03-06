<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import ConnectorCard from '@/modules/bi_analysis_modern/client/src/Connections/components/ConnectorCard.vue'

const searchQuery = ref('')
const router = useRouter()

// Список всех карточек
const allConnectors = [
  { name: 'ClickHouse', icon: '/src/core/bi/assets/icons/clickhouse.svg', category: 'db', route: 'clickhouse' },
  { name: 'Microsoft SQL Server', icon: '/src/core/bi/assets/icons/mssql.svg', category: 'db', route: 'mssql' },
  { name: 'PostgreSQL', icon: '/src/core/bi/assets/icons/postgres.svg', category: 'db', route: 'postgresql' },
  { name: 'Файлы', icon: '/src/core/bi/assets/icons/folder_windows_style.svg', category: 'file', route: 'file' }
]

// Отфильтрованные по поиску
const filteredConnectors = computed(() =>
  allConnectors.filter(c =>
    c.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
)

// Группировка по категориям
const dbConnectors = computed(() =>
  filteredConnectors.value.filter(c => c.category === 'db')
)

const fileConnectors = computed(() =>
  filteredConnectors.value.filter(c => c.category === 'file')
)

function handleClick(route) {
  router.push(`/bi/connections/new/${route}`)
}
</script>

<template>
  <div class="page">
    <!-- Декоративные элементы -->
    <div class="decorative-elements">
      <div class="decorative-circle decorative-circle-1"></div>
      <div class="decorative-circle decorative-circle-2"></div>
      <div class="decorative-circle decorative-circle-3"></div>
    </div>
    
    <div class="page-content">
      <div class="search-wrapper">
        <input 
          class="form-control form-control-sm search-input" 
          type="text" 
          id="smallInput" 
          placeholder="Имя коннектора" 
          v-model="searchQuery" 
          aria-label="Имя коннектора"
        />
      </div>
      
      <div class="category" v-if="dbConnectors.length">
        <h2 class="category-title">Базы данных</h2>
        <div class="cards">
          <ConnectorCard 
            v-for="conn in dbConnectors" 
            :key="conn.name" 
            :name="conn.name" 
            :icon="conn.icon" 
            :type="conn.route"
            @click="handleClick(conn.route)"
          />
        </div>
      </div>
      
      <div class="category" v-if="fileConnectors.length">
        <h2 class="category-title">Файлы и сервисы</h2>
        <div class="cards">
          <ConnectorCard 
            v-for="conn in fileConnectors" 
            :key="conn.name" 
            :name="conn.name" 
            :icon="conn.icon" 
            :type="conn.route"
            @click="handleClick(conn.route)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.page {
  position: relative;
  min-height: 100%;
  padding: 2rem 5rem;
  overflow: hidden;
}

.decorative-elements {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.decorative-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.12;
  animation: float 20s ease-in-out infinite;

  &.decorative-circle-1 {
    top: 10%;
    right: 5%;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(var(--bs-info-rgb), 0.5) 0%, transparent 70%);
    animation-duration: 18s;
  }

  &.decorative-circle-2 {
    bottom: 15%;
    left: 8%;
    width: 280px;
    height: 280px;
    background: radial-gradient(circle, rgba(var(--bs-primary-rgb), 0.4) 0%, transparent 70%);
    animation-duration: 24s;
    animation-delay: -5s;
  }

  &.decorative-circle-3 {
    top: 60%;
    right: 20%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(var(--bs-success-rgb), 0.3) 0%, transparent 70%);
    animation-duration: 30s;
    animation-delay: -10s;
  }
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(30px, -30px) scale(1.1);
  }
  50% {
    transform: translate(-20px, 20px) scale(0.9);
  }
  75% {
    transform: translate(20px, 30px) scale(1.05);
  }
}

.page-content {
  position: relative;
  z-index: 1;
}

.search-wrapper {
  width: 15rem;
  margin-bottom: 2.5rem;
}

.search-input {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

  &:focus {
    background: rgba(255, 255, 255, 0.9);
    border-color: var(--color-accent);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 0 0 3px rgba(var(--bs-info-rgb), 0.1);
    outline: none;
  }
}

.category {
  margin-bottom: 3rem;
}

.category-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary-text);
  margin-bottom: 1.5rem;
  position: relative;
}

.cards {
  display: flex;
  gap: 1.5rem;
  justify-content: flex-start;
  flex-wrap: wrap;
}
</style>
