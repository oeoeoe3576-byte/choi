import { buildHooksPrompt, buildRegenerateHooksPrompt } from '../src/lib/prompts.js'
import { computeHookScore } from '../src/lib/scoring.js'
import { callClaudeJSON } from './_lib/claude.js'
import { withHandler } from './_lib/handler.js'

// 선택된 바이럴 구조에 맞는 훅 후보를 여러 개 생성하고, Hook Score로 채점해 정렬한다.
export default withHandler(async (req, res) => {
  const { topicText, viralTypeId, excludeHooks } = req.body || {}
  if (!topicText || !viralTypeId) {
    res.status(400).json({ error: 'topicText와 viralTypeId가 필요합니다.' })
    return
  }

  const isRegenerate = Array.isArray(excludeHooks) && excludeHooks.length > 0
  const count = isRegenerate ? 5 : 10
  const { system, user } = isRegenerate
    ? buildRegenerateHooksPrompt(topicText, viralTypeId, excludeHooks, count)
    : buildHooksPrompt(topicText, viralTypeId, count)

  const result = await callClaudeJSON({ system, user, maxTokens: 2200 })

  const hooks = (result.hooks || [])
    .map((h) => ({ text: h.text, hookScore: computeHookScore(h.scores) }))
    .sort((a, b) => b.hookScore.total - a.hookScore.total)

  res.status(200).json({ hooks })
})
