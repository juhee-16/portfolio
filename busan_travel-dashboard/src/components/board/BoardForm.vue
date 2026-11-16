<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  initial: { type: Object, default: null },
  mode: { type: String, default: 'create' },
})

const emit = defineEmits(['submit', 'cancel'])

const title = ref(props.initial?.title || '')
const author = ref(props.initial?.author || '익명')
const content = ref(props.initial?.content || '')
const imageUrl = ref(props.initial?.imageUrl || '')
const tagsString = ref((props.initial?.tags || []).join(','))
const password = ref('')

watch(
  () => props.initial,
  (value) => {
    title.value = value?.title || ''
    author.value = value?.author || '익명'
    content.value = value?.content || ''
    imageUrl.value = value?.imageUrl || ''
    tagsString.value = (value?.tags || []).join(', ')
  }
)

function onSubmit() {
  const payload = {
    title: title.value.trim(),
    author: author.value.trim(),
    content: content.value.trim(),
    imageUrl: imageUrl.value.trim(),
    tags: tagsString.value
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean),
  }

  if (props.mode === 'create') {
    payload.password = password.value.trim()
  }

  emit('submit', payload)
}
</script>

<template>
  <form class="board-form" @submit.prevent="onSubmit">
    <label>
      제목
      <input v-model="title" type="text" maxlength="50" required />
    </label>

    <label>
      작성자
      <input v-model="author" type="text" maxlength="20" />
    </label>

    <label>
      내용
      <textarea v-model="content" rows="10" maxlength="2000" required></textarea>
    </label>

    <label>
      이미지 URL
      <input v-model="imageUrl" type="url" placeholder="https://..." />
    </label>

    <label v-if="mode === 'create'">
      비밀번호
      <input
        v-model="password"
        type="password"
        maxlength="20"
        required
        placeholder="수정/삭제 시 필요합니다"
      />
    </label>

    <label>
      태그
      <input v-model="tagsString" type="text" placeholder="여행, 음식, 바다" />
    </label>

    <p class="form-hint">태그는 쉼표로 구분하여 입력하세요.</p>

    <div class="form-actions">
      <button type="submit" class="primary-btn">
        {{ mode === 'edit' ? '수정 완료' : '저장' }}
      </button>
      <button type="button" class="secondary-btn" @click="emit('cancel')">취소</button>
    </div>
  </form>
</template>