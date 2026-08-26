// AI 말투 감지기가 감점 대상으로 보는 문구/이모지 목록.
// 프롬프트에도 그대로 전달해서 생성 단계에서부터 피하게 하고,
// 생성 후에는 여기 정규식으로 한 번 더 클라이언트에서 빠르게 스캔한다.

export const AI_SMELL_PHRASES = [
  '여러분은 어떻게 생각하시나요',
  '여러분의 생각은 어떠신가요',
  '결론적으로',
  '정리하자면',
  '무엇보다 중요한 것은',
  '무엇보다도 중요한 것은',
  '단순히',
  '~을 넘어',
  '을 넘어서',
  '놀랍게도',
  '바로 이것입니다',
  '바로 이거였습니다',
  '이라는 것입니다',
  '것이 아닐까요',
  '해보시는 건 어떨까요',
  '알아보도록 하겠습니다',
  '말씀드리겠습니다',
  '공유해드리려고 합니다',
]

export const AI_SMELL_EMOJI = ['✨', '💡', '✅', '🙌', '👇', '🔥🔥', '💯']

export function scanAiSmell(text) {
  if (!text) return { hits: [], score: 0 }
  const hits = []
  for (const phrase of AI_SMELL_PHRASES) {
    if (text.includes(phrase)) hits.push({ type: 'phrase', value: phrase })
  }
  for (const emoji of AI_SMELL_EMOJI) {
    if (text.includes(emoji)) hits.push({ type: 'emoji', value: emoji })
  }
  // 이모지 총 개수가 과도하게 많은 것도 감점
  const emojiCount = (text.match(/\p{Extended_Pictographic}/gu) || []).length
  if (emojiCount >= 4) hits.push({ type: 'emoji-count', value: `이모지 ${emojiCount}개` })

  const score = Math.min(20, hits.length * 4)
  return { hits, score }
}
