// src/services/commentsService.js — socket 사용 완전 제거 버전 (로컬Storage+BroadcastChannel만 사용)
const CHANNEL_PREFIX = 'busan:comments:'
let storageListener = null
let bc = null

function getStorageKey(postId) {
  return `${CHANNEL_PREFIX}${postId}`
}
function readLocalComments(postId) {
  try { return JSON.parse(localStorage.getItem(getStorageKey(postId))) || [] } catch { return [] }
}
function writeLocalComments(postId, comments) {
  localStorage.setItem(getStorageKey(postId), JSON.stringify(comments))
  if (typeof BroadcastChannel !== 'undefined') {
    if (!bc) bc = new BroadcastChannel('busan-comments')
    bc.postMessage({ postId, comments })
  }
}

export function connectToComments(postId, handlers = {}) {
  const { onInitial = () => {}, onAdd = () => {} } = handlers
  onInitial(readLocalComments(postId))

  // BroadcastChannel or storage event listener
  if (typeof BroadcastChannel !== 'undefined') {
    if (!bc) bc = new BroadcastChannel('busan-comments')
    bc.onmessage = (ev) => {
      if (!ev.data) return
      if (ev.data.postId !== postId) return
      const list = ev.data.comments || []
      if (list.length) onAdd(list[list.length - 1])
    }
  } else {
    storageListener = (ev) => {
      if (!ev.key) return
      if (ev.key !== getStorageKey(postId)) return
      const list = readLocalComments(postId)
      if (list.length) onAdd(list[list.length - 1])
    }
    window.addEventListener('storage', storageListener)
  }

  return () => {
    if (storageListener) {
      window.removeEventListener('storage', storageListener)
      storageListener = null
    }
    if (bc) {
      try {
        bc.close()
      } catch {
        // 이미 닫힌 채널은 무시
      }
      bc = null
    }
  }
}

export async function sendComment(postId, { author, content }) {
  const comment = {
    id: crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
    author: (author && author.trim()) || '익명',
    content: content || '',
    createdAt: Date.now(),
  }
  const list = readLocalComments(postId)
  list.push(comment)
  writeLocalComments(postId, list)
  return comment
}

export function fetchCommentsLocal(postId) {
  return readLocalComments(postId)
}