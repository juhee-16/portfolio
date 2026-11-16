<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  places: { type: Array, default: () => [] },
  selectedPlaceId: { type: [String, Number, null], default: null },
  categories: { type: Array, default: () => [] },
  selectedCategory: { type: String, default: 'all' },
})

const emit = defineEmits(['select', 'change-category'])

const listRef = ref(null)

function scrollToSelected() {
  if (!props.selectedPlaceId || !listRef.value) return

  const target = listRef.value.querySelector(`[data-place-id="${props.selectedPlaceId}"]`)
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

watch(
  () => props.selectedPlaceId,
  () => {
    nextTick(scrollToSelected)
  }
)
</script>

<template>
  <div class="place-browser">
    <div v-if="categories.length" class="category-buttons">
      <button
        v-for="category in categories"
        :key="category.key"
        class="category-btn"
        :class="{ active: selectedCategory === category.key }"
        @click="emit('change-category', category.key)"
      >
        {{ category.label }}
      </button>
    </div>

    <p v-if="places.length === 0" class="status-text">조건에 맞는 장소가 없습니다.</p>

    <div v-else ref="listRef" class="place-list">
      <article
        v-for="place in props.places"
        :key="place.id"
        :data-place-id="place.id"
        class="place-card"
        :class="{ active: props.selectedPlaceId === place.id }"
        @click="emit('select', place.id)"
      >
        <img v-if="place.imageUrl" :src="place.imageUrl" alt="" class="place-image" />
        <div v-else class="place-image place-image--empty">📍</div>

        <div class="place-text">
          <div v-if="place.typeLabel && place.typeLabel !== '맛집 코스'" class="place-type">
            {{ place.typeLabel }}
          </div>
          <h3>{{ place.name }}</h3>
          <p v-if="place.address && place.address !== '주소 없음'">{{ place.address }}</p>
          <div class="place-tags">
            <span v-for="tag in place.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>