export default async (req) => {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method Not Allowed' }), { status: 405 })
  }

  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) {
    console.error(
      '[chat function] OPENAI_API_KEY가 설정되지 않았습니다. netlify dev 실행 위치의 .env 계열 파일을 확인하세요.',
    )
    return new Response(JSON.stringify({ error: 'OPENAI_API_KEY가 설정되지 않았습니다.' }), {
      status: 500,
    })
  }

  let payload
  try {
    payload = await req.json()
  } catch {
    return new Response(JSON.stringify({ error: '잘못된 요청 본문입니다.' }), { status: 400 })
  }

  const message = typeof payload.message === 'string' ? payload.message.slice(0, 500) : ''
  const recommendations = Array.isArray(payload.recommendations)
    ? payload.recommendations.slice(0, 5)
    : []

  const placesText = recommendations
    .map(
      (place) =>
        `- ${place.name} (${place.categoryLabel || place.typeLabel || ''}, ${place.address}): ${place.reason || ''}`,
    )
    .join('\n')

  const systemPrompt = [
    '당신은 부산 여행을 안내하는 다정한 챗봇입니다.',
    '아래 "추천 장소 목록"에 있는 곳만 언급하고, 목록에 없는 장소를 지어내지 마세요.',
    '목록을 그대로 나열하지 말고, 대화하듯 자연스러운 구어체 한국어 2~4문장으로 풀어서 답하세요.',
  ].join(' ')

  const userPrompt = `사용자 메시지: "${message}"\n\n추천 장소 목록:\n${placesText || '(추천할 장소를 찾지 못했습니다)'}`

  try {
    const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || 'gpt-5-mini',
        // reasoning 계열 모델(gpt-5-mini, o1-mini 등)은 커스텀 temperature를 지원하지 않고
        // max_tokens 대신 max_completion_tokens를 쓴다. reasoning에도 토큰이 소모되므로
        // 너무 작게 잡으면 답변이 비어서 나올 수 있어 여유 있게 잡는다.
        max_completion_tokens: 1000,
        // 추천 문구를 자연스럽게 풀어쓰는 정도의 작업이라 깊은 추론이 필요 없다.
        // reasoning_effort를 낮춰서 내부 사고 과정을 줄이고 응답 속도를 개선한다.
        reasoning_effort: 'low',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
      }),
    })

    if (!openaiResponse.ok) {
      const errorBody = await openaiResponse.text()
      console.error('[chat function] OpenAI 호출 실패', openaiResponse.status, errorBody)
      return new Response(JSON.stringify({ error: errorBody }), { status: openaiResponse.status })
    }

    const data = await openaiResponse.json()
    const reply = data.choices?.[0]?.message?.content?.trim() || ''

    return new Response(JSON.stringify({ reply }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (error) {
    console.error('[chat function] 예외 발생', error)
    return new Response(JSON.stringify({ error: error.message }), { status: 500 })
  }
}
