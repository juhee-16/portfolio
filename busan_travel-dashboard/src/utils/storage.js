/**
 * 게시판 LocalStorage 모듈
 */

/** @typedef {import('../type.js').Post} Post */

export const STORAGE_KEYS = {
  POSTS: 'busan:posts',
  CHAT_HISTORY: 'busan:chat-history',
  VIEWED_POSTS: 'busan:viewed-posts',
}

// 데모 시드 게시글의 기본 비밀번호("1234")를 SHA-256으로 미리 해시한 값.
// crypto.subtle.digest는 비동기라 시드 생성 시점에 계산할 수 없어 고정값으로 넣는다.
const SEED_PASSWORD_HASH = '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4'

export class StorageError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'StorageError'
    this.code = code
  }
}

async function hashPassword(password) {
  const data = new TextEncoder().encode(password)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

function createSeedPosts() {
  const now = Date.now()
  return [
    {
      id: 'post-001',
      title: '해운대 야경 보고 왔습니다',
      content:
        '동백섬 산책로 따라 걷다 보면 광안대교가 한눈에 들어와요. 밤 9시쯤이 제일 예뻤습니다.',
      author: '수빈',
      imageUrl: 'https://picsum.photos/seed/haeundae/400/300',
      tags: ['해운대', '야경', '산책'],
      createdAt: now - 1000 * 60 * 60 * 24 * 2,
      updatedAt: now - 1000 * 60 * 60 * 24 * 2,
      viewCount: 12,
      passwordHash: SEED_PASSWORD_HASH,
    },
    {
      id: 'post-002',
      title: '부산 돼지국밥 맛집 추천받아요',
      content: '서면 근처에서 갈 만한 곳 있을까요? 진한 국물 좋아합니다.',
      author: '익명',
      imageUrl: '',
      tags: ['서면', '맛집', '돼지국밥'],
      createdAt: now - 1000 * 60 * 60 * 5,
      updatedAt: now - 1000 * 60 * 60 * 5,
      viewCount: 34,
      passwordHash: SEED_PASSWORD_HASH,
    },
    {
      id: 'post-003',
      title: '감천문화마을 주차 팁',
      content:
        '마을 안까지 차 몰고 들어가지 마세요. 아래쪽 공영주차장에 대고 걸어 올라가는 게 낫습니다.',
      author: '주희',
      imageUrl: 'https://picsum.photos/seed/gamcheon/400/300',
      tags: ['감천문화마을', '주차', '팁'],
      createdAt: now - 1000 * 60 * 30,
      updatedAt: now - 1000 * 60 * 30,
      viewCount: 3,
      passwordHash: SEED_PASSWORD_HASH,
    },
    {
      id: 'post-004',
      title: '광안리 불꽃축제 자리 잡는 법',
      content:
        '오후 3시 전에 민락수변공원 쪽으로 가서 돗자리 펴야 편하게 볼 수 있어요. 화장실 줄도 미리 파악해두세요.',
      author: '동현',
      imageUrl: 'https://picsum.photos/seed/gwangalli/400/300',
      tags: ['광안리', '불꽃축제', '자리'],
      createdAt: now - 1000 * 60 * 60 * 24 * 10,
      updatedAt: now - 1000 * 60 * 60 * 24 * 10,
      viewCount: 87,
      passwordHash: SEED_PASSWORD_HASH,
    },
    {
      id: 'post-005',
      title: '태종대 다누비열차 타는 게 나을까요?',
      content: '걸어서 한 바퀴 도는 거랑 열차 타는 거랑 시간 차이가 얼마나 날까요?',
      author: '익명',
      imageUrl: '',
      tags: ['태종대', '다누비열차'],
      createdAt: now - 1000 * 60 * 60 * 24 * 1,
      updatedAt: now - 1000 * 60 * 60 * 24 * 1,
      viewCount: 21,
      passwordHash: SEED_PASSWORD_HASH,
    },
    {
      id: 'post-006',
      title: '흰여울문화마을 사진 명당 공유합니다',
      content:
        '이송도 해안 산책로 중간쯤에 계단 포토존이 있어요. 오전 10시쯤 가면 사람도 적고 빛도 좋습니다.',
      author: '지민',
      imageUrl: 'https://picsum.photos/seed/huinnyeoul/400/300',
      tags: ['흰여울문화마을', '사진맛집', '산책로'],
      createdAt: now - 1000 * 60 * 60 * 24 * 4,
      updatedAt: now - 1000 * 60 * 60 * 24 * 4,
      viewCount: 45,
      passwordHash: SEED_PASSWORD_HASH,
    },
    {
      id: 'post-007',
      title: '자갈치시장 회 뜨는 곳 가격대 문의',
      content: '2인 기준으로 넉넉하게 먹으려면 예산 얼마 정도 잡아야 할까요?',
      author: '민석',
      imageUrl: '',
      tags: ['자갈치시장', '회', '가격'],
      createdAt: now - 1000 * 60 * 60 * 2,
      updatedAt: now - 1000 * 60 * 60 * 2,
      viewCount: 9,
      passwordHash: SEED_PASSWORD_HASH,
    },
  ]
}

function readPosts() {
  const raw = localStorage.getItem(STORAGE_KEYS.POSTS)

  if (raw === null) {
    const seed = createSeedPosts()
    writePosts(seed)
    return seed
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      throw new Error('배열이 아님')
    }
    return parsed
  } catch {
    throw new StorageError('PARSE_ERROR', '저장된 게시글 데이터를 읽을 수 없습니다.')
  }
}

function writePosts(posts) {
  try {
    localStorage.setItem(STORAGE_KEYS.POSTS, JSON.stringify(posts))
  } catch (err) {
    if (err instanceof DOMException && (err.name === 'QuotaExceededError' || err.code === 22)) {
      throw new StorageError(
        'QUOTA_EXCEEDED',
        '저장 공간이 부족합니다. 기존 게시글을 정리해주세요.',
      )
    }
    throw err
  }
}

export function getAllPosts(options = {}) {
  const { sort = 'latest', keyword = '' } = options

  let result = readPosts()

  if (keyword.trim()) {
    const kw = keyword.trim().toLowerCase()
    result = result.filter(
      (p) => p.title.toLowerCase().includes(kw) || p.content.toLowerCase().includes(kw),
    )
  }

  result.sort((a, b) => (sort === 'latest' ? b.createdAt - a.createdAt : a.createdAt - b.createdAt))

  return result
}

export function getPostById(id) {
  return readPosts().find((p) => p.id === id) ?? null
}

function getViewedPostIds() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEYS.VIEWED_POSTS)
    const parsed = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(parsed) ? parsed : [])
  } catch {
    return new Set()
  }
}

export function increaseViewCount(id) {
  const viewed = getViewedPostIds()
  if (viewed.has(id)) return

  const posts = readPosts()
  const post = posts.find((p) => p.id === id)
  if (!post) return

  post.viewCount += 1
  writePosts(posts)

  viewed.add(id)
  sessionStorage.setItem(STORAGE_KEYS.VIEWED_POSTS, JSON.stringify([...viewed]))
}

export async function createPost(input) {
  const password = input?.password?.trim()
  if (!password) {
    throw new StorageError('PASSWORD_REQUIRED', '수정/삭제 시 필요한 비밀번호를 입력해주세요.')
  }

  const post = {
    id: crypto.randomUUID(),
    title: input?.title?.trim(),
    content: input?.content?.trim(),
    author: input.author?.trim() || '익명',
    imageUrl: input.imageUrl?.trim() || '',
    tags: Array.isArray(input.tags) ? input.tags.map((tag) => tag.trim()).filter(Boolean) : [],
    passwordHash: await hashPassword(password),
    createdAt: Date.now(),
    updatedAt: Date.now(),
    viewCount: 0,
  }

  const posts = readPosts()
  posts.push(post)
  writePosts(posts)

  return post
}

export async function verifyPostPassword(id, password) {
  const post = getPostById(id)
  if (!post) return false
  return (await hashPassword(password || '')) === post.passwordHash
}

export function updatePost(id, patch) {
  const posts = readPosts()
  const post = posts.find((p) => p.id === id)
  if (!post) {
    throw new StorageError('NOT_FOUND', '존재하지 않는 게시글입니다.')
  }

  Object.assign(post, {
    ...patch,
    updatedAt: Date.now(),
    tags: Array.isArray(patch.tags)
      ? patch.tags.map((tag) => tag.trim()).filter(Boolean)
      : post.tags,
  })
  writePosts(posts)

  return post
}

export function deletePost(id) {
  const posts = readPosts()
  const before = posts.length
  const remaining = posts.filter((p) => p.id !== id)

  if (remaining.length === before) return false

  writePosts(remaining)
  return true
}
