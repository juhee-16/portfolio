<script setup>
defineProps({
  post: { type: Object, default: null },
  liked: { type: Boolean, default: false },
  bookmarked: { type: Boolean, default: false },
  likeCount: { type: Number, default: 0 },
})

const emit = defineEmits(['edit', 'delete', 'toggle-like', 'toggle-bookmark'])
</script>

<template>
  <div v-if="post" class="board-detail">
    <div class="detail-header">
      <div>
        <p class="detail-category">여행 게시글</p>
        <h1>{{ post.title }}</h1>
      </div>
      <div class="detail-meta">
        <span>{{ post.author }}</span>
        <span>{{ new Date(post.createdAt).toLocaleString() }}</span>
        <span>조회 {{ post.viewCount }}</span>
      </div>
    </div>

    <div class="board-content">{{ post.content }}</div>

    <div v-if="post.imageUrl" class="detail-image">
      <img :src="post.imageUrl" />
    </div>

    <div v-if="post.tags?.length" class="detail-tags">
      <span v-for="tag in post.tags" :key="tag">{{ tag }}</span>
    </div>

    <div class="detail-actions">
      <button type="button" class="primary-btn" @click="emit('edit')">수정</button>
      <button type="button" class="secondary-btn" @click="emit('delete')">삭제</button>
      <button
        type="button"
        class="secondary-btn like-btn"
        :class="{ liked }"
        @click="emit('toggle-like')"
      >
        <span v-if="liked">❤️</span>
        좋아요 {{ likeCount }}
      </button>
      <button type="button" class="secondary-btn" @click="emit('toggle-bookmark')">
        {{ bookmarked ? '북마크 해제' : '북마크' }}
      </button>
    </div>
  </div>

  <div v-else class="status-card">
    <h3>게시글을 불러오는 중입니다</h3>
  </div>
</template>