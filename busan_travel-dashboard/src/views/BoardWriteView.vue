<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BoardForm from '@/components/board/BoardForm.vue'
import PasswordModal from '@/components/board/PasswordModal.vue'
import { createPost, getPostById, updatePost, verifyPostPassword } from '@/utils/storage.js'

const route = useRoute()
const router = useRouter()

const initial = ref(null)
const isEditMode = ref(false)
const errorMessage = ref('')

const showPasswordGate = ref(false)
const passwordVerified = ref(false)
const passwordError = ref('')

function loadInitial() {
  const id = route.params.id
  if (!id) {
    initial.value = null
    isEditMode.value = false
    passwordVerified.value = true
    showPasswordGate.value = false
    errorMessage.value = ''
    return
  }

  const existing = getPostById(id)
  if (existing) {
    initial.value = existing
    isEditMode.value = true
    passwordVerified.value = false
    passwordError.value = ''
    showPasswordGate.value = true
    errorMessage.value = ''
  } else {
    initial.value = null
    isEditMode.value = false
    errorMessage.value = '존재하지 않는 게시글입니다.'
  }
}

async function handlePasswordConfirm(password) {
  const ok = await verifyPostPassword(route.params.id, password)
  if (!ok) {
    passwordError.value = '비밀번호가 일치하지 않습니다.'
    return
  }

  passwordVerified.value = true
  showPasswordGate.value = false
}

function handlePasswordCancel() {
  showPasswordGate.value = false
  router.back()
}

async function handleSubmit(payload) {
  try {
    if (isEditMode.value) {
      updatePost(route.params.id, payload)
    } else {
      await createPost(payload)
    }
    router.push('/board')
  } catch (error) {
    errorMessage.value = error.message
  }
}

function handleCancel() {
  router.back()
}

onMounted(loadInitial)
watch(() => route.params.id, loadInitial)
</script>

<template>
  <section class="board-write-view">
    <div class="page-header">
      <div>
        <h1>{{ isEditMode ? '게시글 수정' : '게시글 작성' }}</h1>
        <p class="subtitle">
          {{ isEditMode ? '기존 게시글을 수정하세요.' : '새 게시물을 작성하세요.' }}
        </p>
      </div>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <BoardForm
      v-if="!isEditMode || passwordVerified"
      :initial="initial"
      :mode="isEditMode ? 'edit' : 'create'"
      @submit="handleSubmit"
      @cancel="handleCancel"
    />

    <PasswordModal
      :visible="showPasswordGate"
      title="게시글 수정"
      message="수정하려면 작성 시 입력한 비밀번호를 입력하세요."
      :error-message="passwordError"
      confirm-label="확인"
      @confirm="handlePasswordConfirm"
      @cancel="handlePasswordCancel"
    />
  </section>
</template>