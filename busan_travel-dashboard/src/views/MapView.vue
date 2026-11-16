<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PlaceList from '@/components/map/PlaceList.vue'
import { getBookmarks } from '@/services/storageService.js'
import { getPostById } from '@/utils/storage.js'

const router = useRouter()
const searchText = ref('')
const places = ref([])
const selectedPlaceId = ref(null)
const selectedCategory = ref('all')
const bookmarkedPosts = ref([])

const categoryOptions = [
  { key: 'all', label: '전체' },
  { key: 'lodging', label: '숙박' },
  { key: 'culture', label: '문화시설' },
  { key: 'shopping', label: '쇼핑' },
  { key: 'attraction', label: '부산 명소' },
]

const filteredPlaces = computed(() => {
  const text = searchText.value.toLowerCase()

  return places.value.filter((place) => {
    const matchesText =
      place.name.toLowerCase().includes(text) ||
      place.address.toLowerCase().includes(text) ||
      (place.tags || []).some((tag) => tag.toLowerCase().includes(text))

    return matchesText
  })
})

const visiblePlaces = computed(() => {
  if (selectedCategory.value === 'all') {
    return filteredPlaces.value
  }

  return filteredPlaces.value.filter((place) => place.category === selectedCategory.value)
})

function mapItem(item, index, category, typeLabel) {
  return {
    id: item.contentid || `${category}-${index + 1}`,
    name: item.title || '이름 없음',
    address: item.addr1 || '주소 없음',
    category,
    typeLabel,
    imageUrl: item.firstimage || '',
    tags: [item.cat1, item.cat2, item.cat3].filter(Boolean),
  }
}

function normalizePlace(items, category, typeLabel) {
  return (items || []).slice(0, 10).map((item, index) => mapItem(item, index, category, typeLabel))
}

async function loadPlaces() {
  try {
    const [attractionRes, shoppingRes, cultureRes, lodgingRes] = await Promise.all([
      fetch('/data/부산_관광지.json'),
      fetch('/data/부산_쇼핑.json'),
      fetch('/data/부산_문화시설.json'),
      fetch('/data/부산_숙박.json'),
    ])

    const attractionData = await attractionRes.json()
    const shoppingData = await shoppingRes.json()
    const cultureData = await cultureRes.json()
    const lodgingData = await lodgingRes.json()

    const attractionItems = normalizePlace(attractionData.items, 'attraction', '부산 명소')
    const shoppingItems = normalizePlace(shoppingData.items, 'shopping', '쇼핑')
    const cultureItems = normalizePlace(cultureData.items, 'culture', '문화시설')
    const lodgingItems = normalizePlace(lodgingData.items, 'lodging', '숙박')

    places.value = [...attractionItems, ...shoppingItems, ...cultureItems, ...lodgingItems]
  } catch (error) {
    console.error('데이터 로드 실패:', error)
    places.value = []
  }
}

function loadBookmarkedPosts() {
  const bookmarkedIds = getBookmarks()
  bookmarkedPosts.value = bookmarkedIds
    .map((id) => getPostById(id))
    .filter(Boolean)
}

function handleSelectPlace(placeId) {
  selectedPlaceId.value = placeId
}

function changeCategory(category) {
  selectedCategory.value = category
}

function openPost(postId) {
  router.push(`/board/${postId}`)
}

onMounted(() => {
  loadPlaces()
  loadBookmarkedPosts()
})
</script>

<template>
  <div class="main-page">
    <header class="page-header hero-header">
      <div class="hero-overlay">
        <div class="hero-content">
          <div class="hero-title-row">
            <h1>부기와 함께하는 부산 여행</h1>
            <img src="/부기.png" alt="부기" class="hero-bugi" />
          </div>
          <p class="hero-subtitle">부산의 명소와 여행 정보를 한눈에 확인하세요</p>
        </div>

        <div class="weather-card">
          <div class="weather-icon">☀️</div>
          <div>
            <div class="weather-temp">24°C</div>
            <div class="weather-desc">맑음 · 해운대</div>
          </div>
        </div>
      </div>
    </header>

    <section class="main-controls">
      <input
        v-model="searchText"
        type="search"
        placeholder="명소나 쇼핑·숙박 검색"
      />
    </section>

    <section v-if="bookmarkedPosts.length" class="bookmark-section">
      <div class="bookmark-header">
        <h2>북마크한 게시글</h2>
        <p>메인에서 바로 저장한 글을 확인하세요.</p>
      </div>
      <div class="bookmark-list">
        <article
          v-for="post in bookmarkedPosts"
          :key="post.id"
          class="bookmark-item"
          @click="openPost(post.id)"
        >
          <div>
            <h3>{{ post.title }}</h3>
            <p class="bookmark-excerpt">{{ post.content.slice(0, 80) }}...</p>
          </div>
          <button class="secondary-btn">보기</button>
        </article>
      </div>
    </section>

    <section v-else class="bookmark-empty">
      <div class="bookmark-header">
        <h2>북마크한 게시글이 없습니다</h2>
        <p>게시판에서 게시글을 북마크하면 여기서 모아서 볼 수 있어요.</p>
      </div>
    </section>

    <PlaceList
      :places="visiblePlaces"
      :selected-place-id="selectedPlaceId"
      :categories="categoryOptions"
      :selected-category="selectedCategory"
      @select="handleSelectPlace"
      @change-category="changeCategory"
    />
  </div>
</template>