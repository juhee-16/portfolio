<script setup>
defineProps({
  posts: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'delete', 'toggle-like', 'toggle-bookmark'])
</script>

<template>
  <div class="board-list">
    <p v-if="loading" class="status-text">로딩 중...</p>

    <div v-else-if="posts.length === 0" class="status-card">
      <h3>아직 게시글이 없습니다</h3>
      <p>첫 번째 여행 이야기를 남겨보세요.</p>
    </div>

    <div v-else class="board-list-items">
      <article v-for="post in posts" :key="post.id" class="board-item">
        <button type="button" class="board-item-main" @click="emit('select', post.id)">
          <img v-if="post.imageUrl" :src="post.imageUrl" class="board-item-image" />
          <div class="board-item-top">
            <span class="board-badge">여행 이야기</span>
            <span class="board-date">
              {{ new Date(post.createdAt).toLocaleDateString() }}
            </span>
          </div>

          <h2>{{ post.title }}</h2>

          <p class="board-meta">
            {{ post.author }} · 조회 {{ post.viewCount }}
          </p>

          <p class="board-excerpt">{{ post.content }}</p>
        </button>

        <button type="button" class="delete-btn" @click="emit('delete', post.id)">
          삭제
        </button>

        <div class="board-item-actions">
          <button
            type="button"
            class="like-btn"
            :class="{ liked: post.liked }"
            @click.stop="emit('toggle-like', post.id)"
          >
            <span v-if="post.liked">❤️</span>
            좋아요 {{ post.likeCount || 0 }}
          </button>

          <button
            type="button"
            class="bookmark-btn"
            :class="{ bookmarked: post.bookmarked }"
            @click.stop="emit('toggle-bookmark', post.id)"
          >
            {{ post.bookmarked ? '북마크 해제' : '북마크' }}
          </button>
        </div>

        <div v-if="post.tags?.length" class="board-tags">
          <span v-for="tag in post.tags" :key="tag">{{ tag }}</span>
        </div>
      </article>
    </div>
  </div>
</template>