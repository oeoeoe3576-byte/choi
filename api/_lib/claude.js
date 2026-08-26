import Anthropic from '@anthropic-ai/sdk'

let client = null

function getClient() {
  if (!client) {
    const apiKey = process.env.ANTHROPIC_API_KEY
    if (!apiKey) {
      throw new Error(
        'ANTHROPIC_API_KEY가 설정되어 있지 않습니다. .env(로컬) 또는 Vercel 프로젝트 환경변수에 등록하세요.',
      )
    }
    client = new Anthropic({ apiKey })
  }
  return client
}

const MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5'

function extractJSON(text) {
  let cleaned = text.trim()
  const fenceMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (fenceMatch) cleaned = fenceMatch[1].trim()
  try {
    return JSON.parse(cleaned)
  } catch {
    const blockMatch = cleaned.match(/[{[][\s\S]*[}\]]/)
    if (blockMatch) {
      try {
        return JSON.parse(blockMatch[0])
      } catch {
        // fall through
      }
    }
    const err = new Error('AI 응답을 JSON으로 해석하지 못했습니다.')
    err.raw = text
    throw err
  }
}

// system + user 프롬프트로 Claude를 호출하고, 응답을 JSON으로 파싱해 반환한다.
export async function callClaudeJSON({ system, user, maxTokens = 1500 }) {
  const anthropic = getClient()
  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: maxTokens,
    system,
    messages: [{ role: 'user', content: user }],
  })
  const text = (response.content ?? [])
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('')
  return extractJSON(text)
}
