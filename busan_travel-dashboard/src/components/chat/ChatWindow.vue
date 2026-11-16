<script setup>
import { sendChatMessage } from '@/services/recommendService'
import { onMounted, ref } from 'vue'

const emit = defineEmits(['close'])

const messages = ref([])
const input = ref('')
const isLoading = ref(false)
const error = ref('')

const quickOptions = [
  { label: '바다', prompt: '부산에서 바다 보고 싶어요.' },
  { label: '야경', prompt: '부산 야경 좋은 곳 추천해줘.' },
  { label: '가족 여행', prompt: '부산 가족 여행하기 좋은 곳 추천해줘.' },
  { label: '힐링', prompt: '부산에서 힐링하기 좋은 곳 추천해줘.' },
  { label: '쇼핑', prompt: '부산 쇼핑하기 좋은 곳 추천해줘.' },
  { label: '문화', prompt: '부산 문화시설 위주로 추천해줘.' },
]

onMounted(() => {
  messages.value.push({
    role: 'assistant',
    content: '부산 여행 추천을 도와드릴게요. 아래 버튼을 누르거나, 직접 입력해보세요.',
  })
})

async function submitMessage(messageText) {
  const trimmed = messageText.trim()
  if (!trimmed || isLoading.value) return

  error.value = ''
  messages.value.push({ role: 'user', content: trimmed })
  input.value = ''
  isLoading.value = true

  try {
    const response = await sendChatMessage(messages.value)
    messages.value.push({
      role: 'assistant',
      content: response.reply,
      recommendations: response.recommendations || [],
    })
  } catch (err) {
    error.value = err?.message || '전송 실패'
    messages.value.push({
      role: 'assistant',
      content: '추천 요청 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.',
      status: 'error',
    })
  } finally {
    isLoading.value = false
  }
}

function handleSend() {
  submitMessage(input.value)
}

function handleQuickOption(prompt) {
  submitMessage(prompt)
}
</script>

<template>
  <div class="chat-window">
    <div class="chat-header">
      <span>부산 여행 챗봇</span>
      <button type="button" class="chat-close-btn" aria-label="닫기" @click="emit('close')">✕</button>
    </div>

    <div class="chat-messages">
      <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
        <p class="message-text">{{ msg.content }}</p>

        <div v-if="msg.recommendations?.length" class="recommendation-list">
          <div v-for="place in msg.recommendations" :key="place.id" class="recommendation-card">
            <div class="recommendation-title">{{ place.name }}</div>
            <div class="recommendation-meta">{{ place.categoryLabel }} · {{ place.address }}</div>
            <div class="recommendation-reason">{{ place.reason }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="quick-options">
      <button
        v-for="option in quickOptions"
        :key="option.label"
        class="quick-option"
        :disabled="isLoading"
        @click="handleQuickOption(option.prompt)"
      >
        {{ option.label }}
      </button>
    </div>

    <div class="chat-input-area">
      <input
        v-model="input"
        placeholder="예: 바다 보고 싶다, 가족 여행 추천해줘"
        @keydown.enter.prevent="handleSend"
      />
      <button class="send-btn" :disabled="isLoading" @click="handleSend">
        {{ isLoading ? '⏳' : '전송' }}
      </button>
    </div>

    <div v-if="error" class="chat-error">{{ error }}</div>
  </div>
</template>

<style scoped>
.chat-window {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 1150;
  width: min(420px, 100vw);
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 0;
  box-shadow: var(--shadow-lg);
  border-left: 1px solid var(--border-soft);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  background: var(--gradient-brand);
  color: white;
  font-weight: 700;
  flex-shrink: 0;
}

.chat-close-btn {
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
}

.chat-close-btn:hover {
  background: rgba(255, 255, 255, 0.32);
}

.chat-messages {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  overflow-y: auto;
  background: var(--sky-100);
}

.message {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
}

.message.user {
  align-self: flex-end;
  background: var(--gradient-brand);
  color: white;
}

.message.assistant {
  align-self: flex-start;
  background: white;
  color: var(--text-900);
  border: 1px solid var(--border-soft);
}

.message-text {
  margin: 0;
  font-size: 0.95rem;
}

.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recommendation-card {
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  padding: 10px 12px;
  background: var(--sand-100);
}

.recommendation-title {
  font-weight: 700;
  margin-bottom: 2px;
  color: var(--ocean-700);
}

.recommendation-meta {
  font-size: 0.82rem;
  color: var(--text-400);
  margin-bottom: 4px;
}

.recommendation-reason {
  font-size: 0.88rem;
  color: var(--text-600);
}

.quick-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 10px 0;
  border-top: 1px solid var(--border-soft);
}

.quick-option {
  border: 1px solid var(--sky-100);
  background: var(--sky-100);
  color: var(--ocean-700);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.quick-option:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 10px;
}

.chat-input-area input {
  flex: 1;
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
}

.chat-input-area input:focus {
  outline: none;
  border-color: var(--ocean-500);
  box-shadow: 0 0 0 3px rgba(28, 134, 201, 0.15);
}

.send-btn {
  padding: 8px 16px;
  border: none;
  background: var(--gradient-brand);
  color: white;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-error {
  color: #be123c;
  margin: 0 10px 10px;
  font-size: 0.9rem;
}
</style>
