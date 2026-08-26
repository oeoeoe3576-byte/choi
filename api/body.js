import { buildAdjustPrompt, buildBodyPrompt } from '../src/lib/prompts.js'
import { computeHookPayoffScore, computeViralScore } from '../src/lib/scoring.js'
import { scanAiSmell } from '../src/data/aiSmell.js'
import { callClaudeJSON } from './_lib/claude.js'
import { withHandler } from './_lib/handler.js'

async function scoreOnce(system, user) {
  const result = await callClaudeJSON({ system, user, maxTokens: 1600 })
  const hookPayoff = computeHookPayoffScore(result.hookPayoff)
  const smell = scanAiSmell(result.body)

  const penalties = [...(result.penalties || [])]
  if (smell.score > 0 && !penalties.some((p) => p.type === 'aiTone')) {
    penalties.push({
      type: 'aiTone',
      amount: smell.score,
      reason: `AI 말투 감지: ${smell.hits.map((h) => h.value).join(', ')}`,
    })
  }
  if (!hookPayoff.passesThreshold && !penalties.some((p) => p.type === 'hookPayoffMismatch')) {
    penalties.push({
      type: 'hookPayoffMismatch',
      amount: 15,
      reason: 'Hook-Payoff 점수가 75점 미만입니다.',
    })
  }

  const viralScore = computeViralScore(result.viralSub, penalties)
  return { body: result.body, hookPayoff, viralScore, aiSmell: smell }
}

// 본문 생성. Hook-Payoff가 75점 미만이면 한 번 더 시도해 더 나은 쪽을 채택한다(design 5장 규칙).
export default withHandler(async (req, res) => {
  const params = req.body || {}
  const { mode = 'generate' } = params

  let system, user
  if (mode === 'adjust') {
    if (!params.previousBody || !params.instruction) {
      res.status(400).json({ error: 'previousBody와 instruction이 필요합니다.' })
      return
    }
    ;({ system, user } = buildAdjustPrompt(params))
  } else {
    if (!params.topicText || !params.viralTypeId || !params.hookText || !params.length) {
      res.status(400).json({ error: '필수 파라미터가 누락되었습니다.' })
      return
    }
    ;({ system, user } = buildBodyPrompt(params))
  }

  let attempt = await scoreOnce(system, user)
  let retried = false
  if (!attempt.hookPayoff.passesThreshold) {
    const retry = await scoreOnce(system, user)
    retried = true
    if (retry.hookPayoff.score > attempt.hookPayoff.score) attempt = retry
  }

  res.status(200).json({ ...attempt, retried })
})
