<script setup>
import { ref } from 'vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'

const isOpen = ref(false)
</script>

<template>
  <div class="chat-floating">
    <transition name="chat-panel-fade">
      <ChatWindow v-if="isOpen" :is-open="isOpen" @close="isOpen = false" />
    </transition>

    <button class="chat-toggle-btn" :aria-expanded="isOpen" @click="isOpen = !isOpen">
      <span v-if="isOpen">✕</span>
      <span v-else>💬</span>
    </button>
  </div>
</template>

