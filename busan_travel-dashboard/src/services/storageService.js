const STORAGE_KEY = 'busan-travel-dashboard'

function getStore() {
  const raw = localStorage.getItem(STORAGE_KEY)
  return raw ? JSON.parse(raw) : {}
}

function setStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
}

export function getViewCount(postId) {
  const store = getStore()
  return store.views?.[postId] ?? 0
}

export function incrementViewCount(postId) {
  const store = getStore()
  store.views = store.views ?? {}
  store.views[postId] = (store.views[postId] ?? 0) + 1
  setStore(store)
  return store.views[postId]
}

export function getLikeCount(postId) {
  const store = getStore()
  return store.likes?.[postId] ?? 0
}

export function toggleLike(postId) {
  const store = getStore()
  store.likedPosts = store.likedPosts ?? {}
  store.likes = store.likes ?? {}

  const alreadyLiked = !!store.likedPosts[postId]
  store.likedPosts[postId] = !alreadyLiked
  store.likes[postId] = (store.likes[postId] ?? 0) + (alreadyLiked ? -1 : 1)

  setStore(store)
  return store.likes[postId]
}

export function getBookmarks() {
  const store = getStore()
  return store.bookmarks ?? []
}

export function toggleBookmark(postId) {
  const store = getStore()
  store.bookmarks = store.bookmarks ?? []

  const index = store.bookmarks.indexOf(postId)
  const bookmarked = index === -1

  if (bookmarked) {
    store.bookmarks.push(postId)
  } else {
    store.bookmarks.splice(index, 1)
  }

  setStore(store)
  return bookmarked
}

export function isLiked(postId) {
  const store = getStore()
  return !!store.likedPosts?.[postId]
}

export function isBookmarked(postId) {
  const store = getStore()
  return (store.bookmarks || []).includes(postId)
}
