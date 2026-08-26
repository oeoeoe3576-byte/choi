// /api/* 서버리스 함수 호출 헬퍼.
async function post(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.error || `요청 실패 (${res.status})`)
  }
  return data
}

export const analyzeTopic = (topicText) => post('/api/analyze', { topicText })

export const generateHooks = (topicText, viralTypeId, excludeHooks) =>
  post('/api/hooks', { topicText, viralTypeId, excludeHooks })

export const generateBody = (params) => post('/api/body', { mode: 'generate', ...params })

export const adjustBody = (params) => post('/api/body', { mode: 'adjust', ...params })

export const reverseEngineer = (pastedText) => post('/api/reverse-engineer', { pastedText })
