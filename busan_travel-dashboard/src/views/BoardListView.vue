<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BoardList from '@/components/board/BoardList.vue'
import DeleteConfirmModal from '@/components/board/DeleteConfirmModal.vue'
import PasswordModal from '@/components/board/PasswordModal.vue'
import { deletePost, getAllPosts, verifyPostPassword } from '@/utils/storage.js'
import {
  getLikeCount,
  toggleLike,
  toggleBookmark,
  isLiked,
  isBookmarked,
} from '@/services/storageService.js'

const router = useRouter()

const posts = ref([])
const loading = ref(false)
const searchText = ref('')
const errorMessage = ref('')
const showPasswordModal = ref(false)
const showDeleteModal = ref(false)
const passwordError = ref('')
const targetPost = ref(null)

const filteredPosts = computed(() => {
  const query = searchText.value.trim().toLowerCase()
  if (!query) return posts.value

  return posts.value.filter((post) => {
    return (
      post.title.toLowerCase().includes(query) ||
      post.content.toLowerCase().includes(query) ||
      post.author.toLowerCase().includes(query)
    )
  })
})

function loadPosts() {
  loading.value = true
  errorMessage.value = ''

  try {
    const rawPosts = getAllPosts({ sort: 'latest' })
    posts.value = rawPosts.map((post) => ({
      ...post,
      likeCount: getLikeCount(post.id),
      liked: isLiked(post.id),
      bookmarked: isBookmarked(post.id),
    }))
  } catch (error) {
    errorMessage.value = error.message
    posts.value = []
  } finally {
    loading.value = false
  }
}

function handleSelect(id) {
  router.push(`/board/${id}`)
}

function handleDelete(id) {
  const post = posts.value.find((item) => item.id === id)
  if (!post) return

  targetPost.value = post
  passwordError.value = ''
  showPasswordModal.value = true
}

async function handlePasswordConfirm(password) {
  if (!targetPost.value) return

  const ok = await verifyPostPassword(targetPost.value.id, password)
  if (!ok) {
    passwordError.value = '비밀번호가 일치하지 않습니다.'
    return
  }

  showPasswordModal.value = false
  showDeleteModal.value = true
}

function handlePasswordCancel() {
  showPasswordModal.value = false
  targetPost.value = null
}

function confirmDelete() {
  if (!targetPost.value) return

  try {
    const deleted = deletePost(targetPost.value.id)
    if (deleted) {
      posts.value = posts.value.filter((post) => post.id !== targetPost.value.id)
    } else {
      errorMessage.value = '삭제할 수 없는 게시글입니다.'
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    showDeleteModal.value = false
    targetPost.value = null
  }
}

function cancelDelete() {
  showDeleteModal.value = false
  targetPost.value = null
}

function handleWrite() {
  router.push('/board/write')
}

function handleToggleLike(id) {
  const count = toggleLike(id)
  const post = posts.value.find((item) => item.id === id)
  if (post) {
    post.likeCount = count
    post.liked = isLiked(id)
  }
}

function handleToggleBookmark(id) {
  toggleBookmark(id)
  const post = posts.value.find((item) => item.id === id)
  if (post) {
    post.bookmarked = isBookmarked(id)
  }
}

onMounted(loadPosts)
</script>

<template>
  <section class="board-list-view">
    <div class="page-header">
      <div>
        <h1>게시판</h1>
        <p class="subtitle">부산 여행 관련 게시물을 확인하세요.</p>
      </div>
      <button class="primary-btn" @click="handleWrite">글쓰기</button>
    </div>

    <div class="board-search">
      <input v-model="searchText" type="search" placeholder="제목/작성자/내용 검색" />
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <BoardList
      :posts="filteredPosts"
      :loading="loading"
      @select="handleSelect"
      @delete="handleDelete"
      @toggle-like="handleToggleLike"
      @toggle-bookmark="handleToggleBookmark"
    />

    <PasswordModal
      :visible="showPasswordModal"
      title="게시글 삭제"
      message="삭제하려면 작성 시 입력한 비밀번호를 입력하세요."
      :error-message="passwordError"
      confirm-label="확인"
      @confirm="handlePasswordConfirm"
      @cancel="handlePasswordCancel"
    />

    <DeleteConfirmModal
      :visible="showDeleteModal"
      title="게시글 삭제"
      message="이 게시글을 정말 삭제할까요?"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />
  </section>
</template>