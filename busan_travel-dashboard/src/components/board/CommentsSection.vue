<template>
  <section class="comments-section">
    <h3>댓글 ({{ comments.length }})</h3>

    <div v-if="loading" class="status">로딩 중...</div>

    <div v-if="comments.length === 0 && !loading" class="status">첫 댓글을 남겨보세요.</div>

    <ul class="comment-list">
      <li v-for="c in comments" :key="c.id" class="comment-item">
        <div class="meta">
          <strong>{{ c.author }}</strong>
          <small>{{ formatTime(c.createdAt) }}</small>
        </div>
        <div class="content">{{ c.content }}</div>
      </li>
    </ul>

    <form class="comment-form" @submit.prevent="onSubmit">
      <input v-model="author" placeholder="이름 (선택)" />
      <textarea v-model="content" placeholder="댓글을 입력하세요" rows="3"></textarea>
      <div class="actions">
        <button type="submit" class="primary-btn" :disabled="submitting || !content.trim()">댓글 달기</button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { connectToComments, sendComment, fetchCommentsLocal } from '@/services/commentsService'

const props = defineProps({
  postId: { type: String, required: true },
})

const comments = ref([])
const loading = ref(true)
const submitting = ref(false)
const author = ref('')
const content = ref('')

let disconnectFn = null

function formatTime(ts) {
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch {
    return ''
  }
}

async function onSubmit() {
  if (!content.value.trim()) return
  submitting.value = true
  try {
    const created = await sendComment(props.postId, { author: author.value, content: content.value.trim() })
    // optimistic push (server/broadcast will also add)
    comments.value.push(created)
    content.value = ''
  } catch (err) {
    console.error('sendComment error', err)
    alert('댓글 전송에 실패했습니다.')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  // initial load from server/local will be delivered via onInitial
  const onInitial = (list) => {
    comments.value = Array.isArray(list) ? list.slice() : []
    loading.value = false
  }
  const onAdd = (c) => {
    // dedupe
    if (!comments.value.find((x) => x.id === c.id)) comments.value.push(c)
  }

  // attempt to connect (socket or local fallback)
  disconnectFn = connectToComments(props.postId, { onInitial, onAdd })

  // initial local fetch while socket connects quickly
  try {
    const local = fetchCommentsLocal(props.postId)
    if (local && local.length && comments.value.length === 0) {
      comments.value = local.slice()
      loading.value = false
    }
  } catch {
    // localStorage 접근 불가 환경은 무시
  }
})

onUnmounted(() => {
  if (typeof disconnectFn === 'function') disconnectFn()
})
</script>

<style scoped>
.comments-section {
  max-width: 820px;
  margin: 28px auto 0;
  border-top: 1px solid var(--border-soft);
  padding-top: 20px;
}
.comments-section h3 {
  margin: 0 0 12px;
  color: var(--ocean-700);
}
.comment-list {
  list-style: none;
  padding: 0;
  margin: 0 0 16px 0;
}
.comment-item {
  padding: 10px 0;
  border-bottom: 1px dashed var(--border-soft);
}
.comment-item .meta {
  display: flex;
  gap: 8px;
  align-items: baseline;
  font-size: 12px;
  color: var(--text-400);
}
.comment-item .meta strong {
  color: var(--text-900);
}
.comment-item .content {
  margin-top: 6px;
  font-size: 14px;
  color: var(--text-900);
}
.comment-form input,
.comment-form textarea {
  width: 100%;
  border: 1px solid var(--border-soft);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  font-size: 14px;
  box-sizing: border-box;
}
.comment-form input:focus,
.comment-form textarea:focus {
  outline: none;
  border-color: var(--ocean-500);
  box-shadow: 0 0 0 3px rgba(28, 134, 201, 0.15);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
.status {
  color: var(--text-400);
  font-size: 14px;
  margin-bottom: 8px;
}
</style>