import { buildAnalysisPrompt } from '../src/lib/prompts.js'
import { topTypeFits } from '../src/lib/scoring.js'
import { callClaudeJSON } from './_lib/claude.js'
import { withHandler } from './_lib/handler.js'

// 소재를 분석해 7개 요소(공감성/논쟁성/정보성/경험성/놀라움/댓글가능성/신뢰도) 점수를 매기고
// 15개 바이럴 구조 중 적합도 상위 3개를 반환한다.
export default withHandler(async (req, res) => {
  const { topicText } = req.body || {}
  if (!topicText || !topicText.trim()) {
    res.status(400).json({ error: '소재를 입력해주세요.' })
    return
  }

  const { system, user } = buildAnalysisPrompt(topicText)
  const result = await callClaudeJSON({ system, user, maxTokens: 700 })

  const top3 = topTypeFits(result.factors, 3)
  res.status(200).json({
    mainTopic: result.mainTopic,
    subTopic: result.subTopic,
    summary: result.summary,
    factors: result.factors,
    notes: result.notes,
    top3,
  })
})
