<template>
  <div class="main">
    <!-- Декоративные элементы -->
    <div class="decorative-elements">
      <div class="decorative-circle decorative-circle-1"></div>
      <div class="decorative-circle decorative-circle-2"></div>
      <div class="decorative-circle decorative-circle-3"></div>
    </div>
    
    <div class="page-content">
      <transition name="shake">
        <div v-if="isChecked && error && message" class="alert alert-danger" role="alert">
          <OctagonAlert :size="20" class="me-1" /> {{ message }}
        </div>
      </transition>
      <transition name="fade-slide">
        <div v-if="isChecked && !error && message" class="alert alert-success d-flex align-items-center mt-4" role="alert">
          <CircleCheck :size="20" class="me-2" /> {{ message }}
        </div>
      </transition>
      
      <div class="header-section">
        <button @click="goToNewConnection" class="icon-button" title="Назад">
          <ArrowLeft class="icon" />
        </button>
        <div class="logo-wrapper">
          <img :src="logoUrl" :alt="title" :class="['logo', logoClass]" />
          <h2 class="logo-title">{{ title }}</h2>
        </div>
      </div>

      <div class="form-card">
        <form class="main-grid needs-validation" @submit.prevent="$emit('check-connection')" ref="form" novalidate>
          <slot></slot>
          <div class="row_btns">
            <button type="submit" class="btn btn-secondary" :disabled="loading">
              Проверить подключение
            </button>
            <button 
              type="button" 
              class="btn btn-primary" 
              :disabled="loading"
              @click="$emit('create')"
            >
              Создать подключение
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { CircleCheck, OctagonAlert, ArrowLeft } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  logoUrl: {
    type: String,
    required: true
  },
  logoClass: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  },
  error: {
    type: Boolean,
    default: false
  },
  isChecked: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['create', 'check-connection'])
const router = useRouter()
const form = ref(null)

defineExpose({ form })

function goToNewConnection() {
  router.push('/bi-modern/connections/new/')
}
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';
@import '../../scss/_bi-theme.scss';

.main {
  @include bi-burgundy-tokens;
  position: relative;
  min-height: 100%;
  padding: 2rem 5rem;
  overflow: hidden;
  
  @media (max-width: 1400px) {
    padding: 2rem 11rem;
  }

  @media (max-width: 1200px) {
    padding: 2rem 10rem;
  }

  @media (max-width: 992px) {
    padding: 2rem 5rem;
  }

  @media (max-width: 768px) {
    padding: 2rem 2rem;
  }

  @media (max-width: 576px) {
    padding: 2rem 1rem;
  }
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
  max-width: 800px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 2.5rem;
  position: relative;
  gap: 1rem;
}

.logo-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.logo {
  max-height: 80px;
  width: auto;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.1));
}

.logo-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-primary-text);
  margin: 0;
  letter-spacing: -0.02em;
}

.form-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &:hover {
    box-shadow: 
      0 12px 48px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.95);
    background: rgba(255, 255, 255, 0.75);
  }
}

.main-grid {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.row_btns {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  color: var(--color-primary-text);
  border: 1px solid rgba(0, 0, 0, 0.1);

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.95);
    border-color: rgba(var(--bs-info-rgb), 0.2);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }
}

.btn-primary {
  background: linear-gradient(135deg, rgba(var(--bs-danger-rgb), 1) 0%, rgba(var(--bs-danger-rgb), 0.95) 100%);
  color: white;
  box-shadow: 0 3px 6px rgba(var(--bs-danger-rgb), 0.3), 0 1px 3px rgba(0, 0, 0, 0.1);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(var(--bs-danger-rgb), 0.4), 0 2px 6px rgba(0, 0, 0, 0.15);
    background: linear-gradient(135deg, rgba(var(--bs-danger-rgb), 0.98) 0%, rgba(var(--bs-danger-rgb), 0.92) 100%);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(var(--bs-danger-rgb), 0.3);
  }
}

.icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary-text);
  transition: color 0.2s ease;
}

.icon-button {
  position: absolute;
  left: 0;
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);

  &:hover {
    background: rgba(255, 255, 255, 0.9);
    border-color: rgba(var(--bs-info-rgb), 0.2);
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);

    .icon {
      color: var(--color-accent);
    }
  }

  &:active {
    transform: translateY(0);
  }
}

.alert {
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  
  &.alert-danger {
    background: rgba(var(--bs-danger-rgb), 0.1);
    color: var(--bs-danger);
    border-color: rgba(var(--bs-danger-rgb), 0.2);
  }
  
  &.alert-success {
    background: rgba(var(--bs-success-rgb), 0.1);
    color: var(--bs-success);
    border-color: rgba(var(--bs-success-rgb), 0.2);
  }
}

.shake-enter-active {
  animation: shake 0.5s ease;
}

@keyframes shake {
  0% { transform: translateX(0); }
  20% { transform: translateX(-5px); }
  40% { transform: translateX(5px); }
  60% { transform: translateX(-5px); }
  80% { transform: translateX(5px); }
  100% { transform: translateX(0); }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-enter-to,
.fade-slide-leave-from {
  opacity: 1;
  transform: translateY(0);
}
</style>