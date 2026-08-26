import { buildReverseEngineerPrompt } from '../src/lib/prompts.js'
import { callClaudeJSON } from './_lib/claude.js'
import { withHandler } from './_lib/handler.js'

// "터진 글 분석": 붙여넣은 게시물에서 문장이 아닌 구조만 추출한다 (카피 금지).
export default withHandler(async (req, res) => {
  const { pastedText } = req.body || {}
  if (!pastedText || !pastedText.trim()) {
    res.status(400).json({ error: '분석할 게시물을 붙여넣어주세요.' })
    return
  }

  const { system, user } = buildReverseEngineerPrompt(pastedText)
  const result = await callClaudeJSON({ system, user, maxTokens: 900 })
  res.status(200).json(result)
})
