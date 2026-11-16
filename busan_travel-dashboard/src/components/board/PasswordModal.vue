<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '비밀번호 확인' },
  message: { type: String, default: '비밀번호를 입력하세요.' },
  errorMessage: { type: String, default: '' },
  confirmLabel: { type: String, default: '확인' },
})

const emit = defineEmits(['confirm', 'cancel'])

const password = ref('')

watch(
  () => props.visible,
  (value) => {
    if (!value) password.value = ''
  },
)

function onConfirm() {
  if (!password.value) return
  emit('confirm', password.value)
}

function onCancel() {
  password.value = ''
  emit('cancel')
}
</script>

<template>
  <div v-if="props.visible" class="modal-backdrop" @click.self="onCancel">
    <div class="modal-card" role="dialog" aria-modal="true">
      <h3>{{ props.title }}</h3>
      <p>{{ props.message }}</p>

      <input
        v-model="password"
        type="password"
        maxlength="20"
        placeholder="비밀번호"
        class="password-input"
        autofocus
        @keydown.enter.prevent="onConfirm"
      />

      <p v-if="props.errorMessage" class="error-message">{{ props.errorMessage }}</p>

      <div class="modal-actions">
        <button type="button" class="secondary-btn" @click="onCancel">취소</button>
        <button type="button" class="primary-btn" :disabled="!password" @click="onConfirm">
          {{ props.confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.password-input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  box-sizing: border-box;
  margin-top: 14px;
}

.password-input:focus {
  outline: none;
  border-color: var(--ocean-500);
  box-shadow: 0 0 0 3px rgba(28, 134, 201, 0.15);
}
</style>
