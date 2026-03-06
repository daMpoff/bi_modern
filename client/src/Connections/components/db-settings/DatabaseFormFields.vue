<template>
  <div class="row_input" :class="{ 'row_input_full': fullWidth }">
    <label :for="fieldId" class="form-label mb-1">{{ label }}</label>
    <div class="input-wrapper">
      <input 
        :id="fieldId"
        :value="modelValue" 
        @input="$emit('update:modelValue', $event.target.value)"
        :type="type" 
        :required="required"
        :disabled="disabled"
        :class="['form-control', controlClass]"
      />
      <div class="invalid-feedback">{{ errorMessage }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: {
    type: String,
    required: true
  },
  fieldId: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'text'
  },
  required: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  fullWidth: {
    type: Boolean,
    default: false
  },
  controlClass: {
    type: String,
    default: 'form-control-sm'
  },
  errorMessage: {
    type: String,
    default: 'Заполните поле'
  }
})

defineEmits(['update:modelValue'])
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.row_input {
  display: grid;
  grid-template-columns: 200px 1fr;
  align-items: start;
  gap: 1rem;
}

.row_input_full {
  grid-template-columns: 200px 1fr;
}

.input-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
}

.form-label {
  text-align: left;
  font-weight: 600;
  color: var(--color-primary-text);
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

input.form-control {
  height: 40px;
  width: 100%;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);

  &:focus {
    background: rgba(255, 255, 255, 0.95);
    border-color: var(--color-accent);
    box-shadow: 
      0 4px 12px rgba(0, 0, 0, 0.08), 
      0 0 0 3px rgba(var(--bs-info-rgb), 0.1);
    outline: none;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.form-control-port {
  max-width: 7.5rem;
}

.row_input_full input {
  max-width: 100%;
}
</style>