const PLACE_FILES = [
  { path: '/data/부산_관광지.json', category: 'attraction', label: '부산 명소' },
  { path: '/data/부산_문화시설.json', category: 'culture', label: '문화시설' },
  { path: '/data/부산_쇼핑.json', category: 'shopping', label: '쇼핑' },
  { path: '/data/부산_숙박.json', category: 'lodging', label: '숙박' },
]

const CATEGORY_LABELS = {
  attraction: '부산 명소',
  culture: '문화시설',
  shopping: '쇼핑',
  lodging: '숙박',
}

let cachedPlaces = null
let pendingPlaces = null

function normalizePlace(item, index, category, typeLabel) {
  const tags = [item.cat1, item.cat2, item.cat3].filter(Boolean)
  const name = item.title || '이름 없음'
  const address = item.addr1 || '주소 없음'

  return {
    id: item.contentid || `${category}-${index + 1}`,
    name,
    address,
    category,
    typeLabel,
    tags,
    description: item.overview || '',
  }
}

async function loadPlaces() {
  if (cachedPlaces) return cachedPlaces
  if (pendingPlaces) return pendingPlaces

  pendingPlaces = (async () => {
    const responses = await Promise.all(
      PLACE_FILES.map(async ({ path, category, label }) => {
        const response = await fetch(path)
        if (!response.ok) {
          throw new Error(`${label} 데이터를 불러오지 못했습니다.`)
        }

        const data = await response.json()
        return (data.items || [])
          .slice(0, 10)
          .map((item, index) => normalizePlace(item, index, category, label))
      }),
    )

    cachedPlaces = responses.flat()
    return cachedPlaces
  })()

  try {
    return await pendingPlaces
  } finally {
    pendingPlaces = null
  }
}

// 추상 무드 키워드가 아니라, 실제 장소 이름/주소에 등장할 법한 구체적인 단어들로
// 테마를 정의한다. (예: '바다'라는 추상어 대신 '해운대', '광안' 같은 실제 지명으로 매칭)
const THEMES = [
  {
    key: '바다',
    terms: ['바다', '해변', '해운대', '광안', '다대', '송도', '해수욕장', '바닷가', '송정', '오륙도', '태종대'],
    reason: '바다 분위기와 잘 어울립니다',
  },
  {
    key: '야경',
    terms: ['야경', '야시장', '불빛', '불꽃', '달맞이', '광안대교'],
    reason: '야경 감상이 좋습니다',
  },
  {
    key: '가족',
    terms: ['가족', '아이', '어린이', '키즈', 'kids', 'child'],
    reason: '가족 여행객에게 적합합니다',
  },
  {
    key: '데이트',
    terms: ['커플', '데이트', '로맨틱'],
    reason: '데이트 코스로 만족도가 높습니다',
  },
  {
    key: '힐링',
    terms: ['힐링', '산책', '둘레길', '공원', '휴식'],
    reason: '잔잔하게 쉬기 좋습니다',
  },
  {
    key: '쇼핑',
    terms: ['쇼핑', '시장', '상가', '백화점', '아울렛'],
    reason: '쇼핑과 연결하기 좋습니다',
    category: 'shopping',
  },
  {
    key: '문화',
    terms: ['문화', '전시', '미술', '공연', '박물관', '예술'],
    reason: '문화 체험 요소가 있습니다',
    category: 'culture',
  },
  {
    key: '맛집',
    terms: ['맛집', '먹거리', '국밥', '해산물', '시장'],
    reason: '먹거리와 연계하기 좋습니다',
  },
]

const LODGING_TERMS = ['숙박', '호텔', '펜션', '머물', '하루', 'stay']
const ATTRACTION_TERMS = ['명소', '관광', '사진', '카페', '산책']

export function extractPreferences(text = '') {
  const normalized = text.toLowerCase()

  const themes = THEMES.filter((theme) =>
    theme.terms.some((term) => normalized.includes(term.toLowerCase())),
  )

  const categories = new Set()
  if (LODGING_TERMS.some((term) => normalized.includes(term))) categories.add('lodging')
  if (ATTRACTION_TERMS.some((term) => normalized.includes(term))) categories.add('attraction')
  themes.forEach((theme) => {
    if (theme.category) categories.add(theme.category)
  })

  return { themes, categories: [...categories] }
}

function placeSearchText(place) {
  return `${place.name} ${place.address} ${place.typeLabel}`.toLowerCase()
}

function scorePlace(place, preferences) {
  const { themes = [], categories = [] } = preferences
  const text = placeSearchText(place)
  let score = 0

  if (categories.includes(place.category)) score += 5

  themes.forEach((theme) => {
    if (theme.terms.some((term) => text.includes(term.toLowerCase()))) {
      score += 3
    }
  })

  return score
}

// 배열을 무작위로 섞는다. 동점 장소가 항상 같은 순서(원본 배열 순서)로 뽑히는 걸 막기 위함.
function shuffle(list) {
  const copy = [...list]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export function pickRecommendations(places, message = '') {
  const preferences = extractPreferences(message)
  const scored = places.map((place) => ({ ...place, score: scorePlace(place, preferences) }))

  const matched = scored.filter((place) => place.score > 0)
  const pool = matched.length > 0 ? matched : scored

  const top = shuffle(pool)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)

  return top.map((place) => ({
    ...place,
    categoryLabel: CATEGORY_LABELS[place.category] || place.category,
    reason: buildReason(place, preferences),
  }))
}

function buildReason(place, preferences) {
  const { themes = [] } = preferences
  const text = placeSearchText(place)
  const matchedThemes = themes.filter((theme) =>
    theme.terms.some((term) => text.includes(term.toLowerCase())),
  )

  if (matchedThemes.length === 0) {
    return `${place.typeLabel} 중에서 여행 초보에게 추천하기 좋은 곳입니다.`
  }

  return matchedThemes.map((theme) => theme.reason).join(' · ')
}

function buildReply(message, recommendations) {
  const trimmed = message.trim()
  const intro = trimmed
    ? `“${trimmed}”에 맞춰 부산 여행지 ${recommendations.length}곳을 골라봤어요.`
    : '어떤 분위기의 부산 여행을 원하시는지 말해 주세요.'

  const list = recommendations
    .map((place) => `- ${place.name} (${place.categoryLabel}) : ${place.reason}`)
    .join('\n')

  const followUp =
    '원하면 제가 바다, 야경, 가족 여행, 힐링, 쇼핑처럼 세부 분위기까지 더 맞춰서 추천해드릴게요.'

  return `${intro}\n\n${list}\n\n${followUp}`
}

// GPT로 자연스러운 문장을 생성. 로컬 dev(순수 vite)나 API 실패/키 미설정 시엔 null을 반환해
// 호출부에서 기존 템플릿(buildReply)으로 조용히 폴백하도록 한다.
async function generateNaturalReply(message, recommendations) {
  try {
    const response = await fetch('/.netlify/functions/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, recommendations }),
    })

    if (!response.ok) {
      const errorBody = await response.text().catch(() => '')
      console.warn(
        `[chatbot] GPT 응답 생성 실패(${response.status}) → 템플릿 응답으로 대체합니다.`,
        errorBody,
      )
      return null
    }

    const data = await response.json()
    if (!data.reply) {
      console.warn('[chatbot] GPT 응답이 비어 있어 템플릿 응답으로 대체합니다.')
      return null
    }

    return data.reply.trim()
  } catch (error) {
    console.warn('[chatbot] /.netlify/functions/chat 호출 실패 → 템플릿 응답으로 대체합니다.', error)
    return null
  }
}

export async function sendChatMessage(history = []) {
  const lastUserMessage =
    [...history].reverse().find((message) => message.role === 'user')?.content || ''
  const places = await loadPlaces()
  const recommendations = pickRecommendations(places, lastUserMessage)

  const naturalReply = await generateNaturalReply(lastUserMessage, recommendations)

  return {
    reply: naturalReply || buildReply(lastUserMessage, recommendations),
    recommendations,
    intent: 'recommend',
  }
}
