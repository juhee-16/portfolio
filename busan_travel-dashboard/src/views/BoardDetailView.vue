<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BoardDetail from '@/components/board/BoardDetail.vue'
import DeleteConfirmModal from '@/components/board/DeleteConfirmModal.vue'
import PasswordModal from '@/components/board/PasswordModal.vue'
import { deletePost, getPostById, increaseViewCount, verifyPostPassword } from '@/utils/storage.js'
import CommentsSection from '@/components/board/CommentsSection.vue'
import { getLikeCount, toggleLike, isLiked, isBookmarked, toggleBookmark } from '@/services/storageService.js'

const route = useRoute()
const router = useRouter()

const post = ref(null)
const errorMessage = ref('')
const showPasswordModal = ref(false)
const showDeleteModal = ref(false)
const passwordError = ref('')
const liked = ref(false)
const bookmarked = ref(false)
const likeCount = ref(0)

function loadPost() {
  const id = route.params.id
  const current = getPostById(id)

  if (!current) {
    post.value = null
    errorMessage.value = '존재하지 않는 게시글입니다.'
    return
  }

  increaseViewCount(id)
  post.value = getPostById(id)
  errorMessage.value = ''
}

function syncReactionState() {
  if (!post.value) {
    liked.value = false
    bookmarked.value = false
    likeCount.value = 0
    return
  }

  liked.value = isLiked(post.value.id)
  bookmarked.value = isBookmarked(post.value.id)
  likeCount.value = getLikeCount(post.value.id)
}

function handleEdit() {
  if (!post.value) return
  router.push(`/board/write/${post.value.id}`)
}

function handleDelete() {
  passwordError.value = ''
  showPasswordModal.value = true
}

async function handlePasswordConfirm(password) {
  if (!post.value) return

  const ok = await verifyPostPassword(post.value.id, password)
  if (!ok) {
    passwordError.value = '비밀번호가 일치하지 않습니다.'
    return
  }

  showPasswordModal.value = false
  showDeleteModal.value = true
}

function handlePasswordCancel() {
  showPasswordModal.value = false
}

function confirmDelete() {
  if (!post.value) return

  try {
    const deleted = deletePost(post.value.id)
    if (deleted) {
      router.push('/board')
    } else {
      errorMessage.value = '삭제할 수 없는 게시글입니다.'
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    showDeleteModal.value = false
  }
}

function cancelDelete() {
  showDeleteModal.value = false
}

function handleToggleLike() {
  if (!post.value) return
  toggleLike(post.value.id)
  liked.value = isLiked(post.value.id)
  likeCount.value = getLikeCount(post.value.id)
}

function handleToggleBookmark() {
  if (!post.value) return
  toggleBookmark(post.value.id)
  bookmarked.value = isBookmarked(post.value.id)
}

onMounted(loadPost)
watch(() => route.params.id, loadPost)
watch(post, syncReactionState)
</script>

<template>
  <section class="board-detail-view">
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <BoardDetail
      :post="post"
      :liked="liked"
      :bookmarked="bookmarked"
      :like-count="likeCount"
      @toggle-like="handleToggleLike"
      @toggle-bookmark="handleToggleBookmark"
      @edit="handleEdit"
      @delete="handleDelete"
    />

    <CommentsSection v-if="post" :post-id="post.id" />

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