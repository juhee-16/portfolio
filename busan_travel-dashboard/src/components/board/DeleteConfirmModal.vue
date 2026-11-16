<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '확인' },
  message: { type: String, default: '정말 진행할까요?' },
})

const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <div v-if="props.visible" class="modal-backdrop" @click.self="emit('cancel')">
    <div class="modal-card" role="dialog" aria-modal="true">
      <h3>{{ props.title }}</h3>
      <p>{{ props.message }}</p>

      <div class="modal-actions">
        <button type="button" class="secondary-btn" @click="emit('cancel')">취소</button>
        <button type="button" class="delete-btn" @click="emit('confirm')">삭제</button>
      </div>
    </div>
  </div>
</template>