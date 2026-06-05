<template>
  <div class="card" @click="handleClick">
    <a class="a_link">
      <img :src="icon" class="card-icon" />
      <div class="card_title">{{ name }}</div>
    </a>
  </div>
</template>
  
<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  name: String,
  icon: [String, Object],
  type: String
})

const emit = defineEmits(['click'])

const router = useRouter()

function handleClick() {
  if (props.type) {
    emit('click', props.type)
    router.push(`/bi-modern/connections/new/${props.type}`)
  }
}
</script>
  
<style scoped lang="scss">
@import '@/scss/_variables.scss';
@import '../../scss/_bi-theme.scss';

.card {
  width: 163px;
  height: 114px;
  background: var(--color-primary-background);
  border-radius: 12px;
  cursor: pointer;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--color-border);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba($bi-accent, 0.5) 50%,
      transparent 100%);
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  &:hover {
    border-color: rgba($bi-accent, 0.4);
    transform: translateY(-3px);
    box-shadow:
      0 6px 18px rgba(0, 0, 0, 0.10),
      0 2px 6px rgba($bi-accent, 0.15);

    &::before {
      opacity: 1;
    }

    .card-icon {
      transform: scale(1.1);
      filter: brightness(1.05);
    }
  }

  &:active {
    transform: translateY(-1px);
  }
}

.card-icon {
  width: 56px;
  height: 56px;
  margin-bottom: 0.75rem;
  color: var(--color-primary-text);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.card_title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary-text);
  text-align: center;
  line-height: 1.4;
  transition: color 0.3s ease;
}

.card:hover .card_title {
  color: $bi-accent;
}

.a_link {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
}
</style>