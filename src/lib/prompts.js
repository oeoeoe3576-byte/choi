import { ANALYSIS_FACTORS, VIRAL_TYPES, CONVERSATION_TRIGGER_STYLES, getViralType } from '../data/viralTypes.js'
import { AI_SMELL_PHRASES, AI_SMELL_EMOJI } from '../data/aiSmell.js'

const BANNED_PHRASES = AI_SMELL_PHRASES.map((p) => `"${p}"`).join(', ')
const BANNED_EMOJI = AI_SMELL_EMOJI.join(' ')

const HOUSE_STYLE = `
글은 Threads(스레드) 게시물이다. 다음 문체 규칙을 반드시 지킨다.
- 사람이 스마트폰으로 편하게 쓴 것처럼 자연스럽게 쓴다. 완벽하게 다듬어진 문장은 오히려 부자연스럽다.
- 절대 쓰지 않는 문구: ${BANNED_PHRASES}
- 절대 쓰지 않는(과도한) 이모지: ${BANNED_EMOJI} — 이모지는 아예 안 쓰거나 최대 1개만.
- "여러분은 어떻게 생각하세요?" 같은 뻔한 질문으로 끝내지 않는다.
- 존재하지 않는 통계, 숫자, 조회수, 사례를 지어내지 않는다. 사용자가 제공한 사실만 사용한다.
- 반말/구어체 톤을 기본으로 하되 과격한 어그로나 혐오, 비하는 쓰지 않는다.
`.trim()

// ── 1) 소재 분석 ────────────────────────────────────────────
export function buildAnalysisPrompt(topicText) {
  const factorList = ANALYSIS_FACTORS.map((f) => `- ${f.key} (${f.label}): ${f.hint}`).join('\n')
  const system = `너는 Threads 바이럴 구조 분석가다. 사용자가 던진 소재를 읽고, "이 소재가 왜 사람들에게 흥미로울 수 있는지"를 분석한다.
글을 바로 쓰지 않는다. 오직 분석만 한다.

다음 7개 요소를 각각 0~10점으로 채점한다:
${factorList}

그리고 mainTopic(대주제, 예: 여행), subTopic(소주제, 예: 일본여행), summary(이 소재의 핵심 후킹 포인트를 1문장으로)를 뽑는다.
점수는 사용자가 입력한 내용에 실제로 근거해야 한다. 근거 없이 후하게 주지 않는다.

반드시 아래 JSON 스키마로만 답한다. 다른 텍스트, 코드펜스, 설명 없이 JSON만 출력한다.
{
  "mainTopic": string,
  "subTopic": string,
  "summary": string,
  "factors": { "empathy": number, "controversy": number, "information": number, "experience": number, "surprise": number, "commentability": number, "credibility": number },
  "notes": string  // 분석 근거를 1~2문장으로
}`
  const user = `소재:\n${topicText}`
  return { system, user }
}

// ── 2) 훅 후보 생성 + 자가채점 ───────────────────────────────
export function buildHooksPrompt(topicText, viralTypeId, count = 10) {
  const type = getViralType(viralTypeId)
  const system = `너는 Threads 후킹 문장(첫 1~3줄) 전문가다.
아래 "바이럴 구조"에 맞춰 소재로부터 서로 다른 후킹 문장 후보를 ${count}개 만든다.

바이럴 구조: ${type.name} (${type.oneLiner})
구조 설명: ${type.structureHint}
예시 톤(그대로 베끼지 말 것): "${type.example}"

각 후보를 만든 뒤 스스로 아래 기준으로 0~1 사이 점수를 매긴다(소수 둘째자리까지):
- curiosity: 다음 문장이 궁금해지는가
- specificity: 구체적인가 (막연한 일반론이 아닌가)
- relatability: "내 얘기"처럼 느껴지는가
- tension: 갈등/의외성/긴장이 있는가
- novelty: 뻔하지 않은가
- naturalness: 사람이 편하게 쓴 것처럼 자연스러운가 (AI 말투 감지 규칙 위반 시 0.2 이하로 채점)

${HOUSE_STYLE}
후킹 문장은 실제 게시물의 첫 1~3줄이 될 문장이다. 본문 전체를 쓰지 않는다.

반드시 아래 JSON 스키마로만 답한다.
{
  "hooks": [
    { "text": string, "scores": { "curiosity": number, "specificity": number, "relatability": number, "tension": number, "novelty": number, "naturalness": number } }
  ]
}
정확히 ${count}개를 만든다.`
  const user = `소재:\n${topicText}`
  return { system, user }
}

// ── 3) 본문 생성 (선택된 훅 기반) ─────────────────────────────
export function buildBodyPrompt({ topicText, viralTypeId, hookText, length, ctaStyleId, factors, mainTopic, subTopic }) {
  const type = getViralType(viralTypeId)
  const lengthSpec = {
    short: '2~5줄. 드립/관찰/질문 위주로 짧게. 구조를 다 채우려 하지 말 것.',
    medium: '5~10줄. Threads 기본 길이. HOOK → 상황 → 핵심/반전 → 근거(경험) → 한 줄 결론 흐름을 자연스럽게.',
    story: '10~18줄. 스토리텔링. 시간 흐름이나 감정 변화를 보여주며 천천히 풀어간다.',
  }[length]
  const ctaStyle = CONVERSATION_TRIGGER_STYLES.find((c) => c.id === ctaStyleId)

  const system = `너는 Threads 게시물 작가다. 아래 정보로 본문을 작성한다.

바이럴 구조: ${type.name} — ${type.structureHint}
길이: ${length.toUpperCase()} (${lengthSpec})
Conversation Trigger 스타일: ${ctaStyle.label} — 예: "${ctaStyle.example}"${ctaStyleId === 'none' ? ' (질문으로 끝내지 말고 문장으로 마무리)' : ''}
대주제/소주제: ${mainTopic ?? ''} / ${subTopic ?? ''}

이 게시물은 반드시 주어진 훅(첫 문장)으로 시작해야 한다:
"${hookText}"

${HOUSE_STYLE}

본문 작성 후 스스로 아래 두 가지를 채점한다:

1) Hook-Payoff (훅이 약속한 것을 본문이 실제로 보상하는가), 각 0~1:
   - promiseKept: 훅이 암시한 내용을 본문이 실제로 전달하는가
   - depthMatch: 훅의 긴장감/기대치에 맞는 깊이인가 (훅은 세게 던지고 내용은 시시하면 낮게)
   - noBaitAndSwitch: 낚시성으로 다른 얘기로 새지 않았는가

2) Viral Potential 세부 점수(각 0~1):
   - firstLine, curiosity, empathy, opinionPotential, specificity, infoOrExperienceValue, naturalness, topicFit

3) penalties: 아래 항목에 해당하면 배열에 추가. 해당 없으면 빈 배열.
   - aiTone (AI 말투가 남아있음, amount 5~20)
   - excessiveBait (과도한 어그로/자극, amount 5~30)
   - hookPayoffMismatch (훅과 본문 불일치, amount 10~40)
   - unfoundedNumbers (근거 없는 숫자를 지어냄, amount 30)
   - fakeExperience (가짜 경험을 지어냄, amount 50)

반드시 아래 JSON 스키마로만 답한다.
{
  "body": string,
  "hookPayoff": { "promiseKept": number, "depthMatch": number, "noBaitAndSwitch": number },
  "viralSub": { "firstLine": number, "curiosity": number, "empathy": number, "opinionPotential": number, "specificity": number, "infoOrExperienceValue": number, "naturalness": number, "topicFit": number },
  "penalties": [ { "type": string, "amount": number, "reason": string } ]
}`

  const factorSummary = factors
    ? ANALYSIS_FACTORS.map((f) => `${f.label}:${factors[f.key] ?? '-'}`).join(', ')
    : ''
  const user = `소재:\n${topicText}\n\n소재 분석 점수: ${factorSummary}`
  return { system, user }
}

// ── 4) 본문 재조정 (더 세게 / 덜 자극적으로 / 더 자연스럽게 / 다른 훅) ──
export const ADJUST_INSTRUCTIONS = {
  stronger: '긴장감과 후킹력을 더 세게 만든다. 단, 근거 없는 과장이나 거짓 경험은 추가하지 않는다.',
  softer: '어그로/자극을 줄이고 더 담백하게 만든다. 정보/경험의 핵심은 유지한다.',
  natural: 'AI 말투를 더 제거하고 사람이 편하게 쓴 것처럼 자연스럽게 다듬는다. 문장 길이를 들쭉날쭉하게 만들어도 좋다.',
}

export function buildAdjustPrompt({ topicText, viralTypeId, hookText, previousBody, length, instruction }) {
  const type = getViralType(viralTypeId)
  const instructionText = ADJUST_INSTRUCTIONS[instruction] ?? instruction
  const system = `너는 Threads 게시물을 수정하는 편집자다. 아래 기존 게시물을 다음 지시에 맞게 다시 쓴다: ${instructionText}

바이럴 구조: ${type.name}
길이는 기존과 동일하게 유지: ${length.toUpperCase()}
훅(첫 문장)은 특별한 지시가 없는 한 유지: "${hookText}"

${HOUSE_STYLE}

수정 후 이전과 동일한 채점을 스스로 수행한다.
반드시 아래 JSON 스키마로만 답한다.
{
  "body": string,
  "hookPayoff": { "promiseKept": number, "depthMatch": number, "noBaitAndSwitch": number },
  "viralSub": { "firstLine": number, "curiosity": number, "empathy": number, "opinionPotential": number, "specificity": number, "infoOrExperienceValue": number, "naturalness": number, "topicFit": number },
  "penalties": [ { "type": string, "amount": number, "reason": string } ]
}`
  const user = `소재:\n${topicText}\n\n기존 게시물:\n${previousBody}`
  return { system, user }
}

// ── 5) 다른 훅 후보 다시 뽑기 (동일 유형, 이전 후보 제외) ─────────
export function buildRegenerateHooksPrompt(topicText, viralTypeId, excludeHooks = [], count = 5) {
  const base = buildHooksPrompt(topicText, viralTypeId, count)
  const excludeText = excludeHooks.length
    ? `\n\n다음 문장들과 겹치거나 비슷한 표현은 피하고 새로운 각도로 만든다:\n${excludeHooks.map((h) => `- ${h}`).join('\n')}`
    : ''
  return { system: base.system + excludeText, user: base.user }
}

// ── 6) 터진 글 구조 분석 (레퍼런스 리버스 엔지니어링) ─────────────
export function buildReverseEngineerPrompt(pastedText) {
  const typeList = VIRAL_TYPES.map((t) => `${t.id}: ${t.name} (${t.oneLiner})`).join('\n')
  const system = `너는 바이럴 게시물 구조 분석가다. 사용자가 붙여넣은, 실제로 반응이 좋았던 게시물을 분석한다.

절대 원문 문장을 그대로 재사용하지 않는다. 오직 "구조"만 추출한다. 목적은 카피가 아니라 패턴 학습이다.

아래를 분석한다:
- hook: 훅이 사용한 기법 요약 (원문 인용 아님, 기법 설명)
- hookMechanism: 상식반전 / 손실회피 / 공감 / 호기심갭 / 갈등 등 어떤 심리 기제를 썼는지
- emotion: 이 글이 자극하는 주된 감정
- mechanism: 글의 전개 순서를 일반화한 구조 (예: "나는 ○○을 오래 했지만 → 뒤늦게 ○○을 발견 → 기존 믿음 부정 → 새로운 결론")
- conversationGap: 댓글을 유도하는 여지가 얼마나 큰지 (낮음/중간/높음)과 이유
- matchedViralType: 아래 15개 유형 중 가장 가까운 것의 id
${typeList}
- structureTemplate: 다른 소재에도 재사용 가능하도록 일반화한 문장 템플릿 (플레이스홀더 사용, 예: "[오래 해온 일]을 오래 했지만 최근에야 [반전 정보]를 알게 됐다")

반드시 아래 JSON 스키마로만 답한다.
{
  "hook": string,
  "hookMechanism": string,
  "emotion": string,
  "mechanism": string,
  "conversationGap": { "level": "낮음" | "중간" | "높음", "reason": string },
  "matchedViralType": string,
  "structureTemplate": string
}`
  const user = `분석할 게시물:\n${pastedText}`
  return { system, user }
}
