// 점수 계산은 전부 결정적(deterministic) 함수로 만든다.
// LLM은 각 세부 항목의 "부분 점수"만 채점하고, 합산·가중치·페널티 적용은
// 여기서 코드로 고정한다 — 총점을 LLM이 직접 부르게 두면 일관성이 떨어진다.

import { ANALYSIS_FACTORS, VIRAL_TYPES } from '../data/viralTypes.js'

const clamp = (n, min, max) => Math.max(min, Math.min(max, n))

// ── 1) 소재 분석 → 15개 유형 적합도 ─────────────────────────────
// factors: { empathy, controversy, information, experience, surprise, commentability, credibility } (0~10)
export function computeTypeFits(factors) {
  return VIRAL_TYPES.map((type) => {
    let weightedSum = 0
    let weightTotal = 0
    for (const f of ANALYSIS_FACTORS) {
      const score = clamp(Number(factors?.[f.key] ?? 0), 0, 10)
      const w = type.weights[f.key] ?? 0
      weightedSum += score * w
      weightTotal += w
    }
    // 0~10 스케일의 가중평균을 100점 만점으로 변환
    const fit = weightTotal > 0 ? Math.round((weightedSum / weightTotal) * 10) : 0
    return { ...type, fit: clamp(fit, 0, 100) }
  }).sort((a, b) => b.fit - a.fit)
}

export function topTypeFits(factors, n = 3) {
  return computeTypeFits(factors).slice(0, n)
}

// ── 2) 훅 점수 (Hook Score, 100점) ─────────────────────────────
// sub: { curiosity, specificity, relatability, tension, novelty, naturalness } — 각 항목 0~1 비율로 받음(LLM이 0~1로 채점)
const HOOK_WEIGHTS = {
  curiosity: 25,
  specificity: 20,
  relatability: 20,
  tension: 15,
  novelty: 10,
  naturalness: 10,
}

export function computeHookScore(sub = {}) {
  let total = 0
  const breakdown = {}
  for (const [key, max] of Object.entries(HOOK_WEIGHTS)) {
    const ratio = clamp(Number(sub[key] ?? 0), 0, 1)
    const points = Math.round(ratio * max)
    breakdown[key] = points
    total += points
  }
  return { total: clamp(total, 0, 100), breakdown }
}

// ── 3) Hook–Payoff 점수 (100점, 75점 미만이면 재작성) ─────────────
// sub: { promiseKept, depthMatch, noBaitAndSwitch } 각 0~1
export function computeHookPayoffScore(sub = {}) {
  const weights = { promiseKept: 50, depthMatch: 30, noBaitAndSwitch: 20 }
  let total = 0
  for (const [key, max] of Object.entries(weights)) {
    total += clamp(Number(sub[key] ?? 0), 0, 1) * max
  }
  const score = clamp(Math.round(total), 0, 100)
  return { score, passesThreshold: score >= 75 }
}

// ── 4) 최종 Viral Potential Score (100점 + 페널티) ─────────────
const VIRAL_WEIGHTS = {
  firstLine: 20,
  curiosity: 15,
  empathy: 15,
  opinionPotential: 15,
  specificity: 10,
  infoOrExperienceValue: 10,
  naturalness: 10,
  topicFit: 5,
}

export const PENALTY_RANGES = {
  aiTone: [5, 20],
  excessiveBait: [5, 30],
  hookPayoffMismatch: [10, 40],
  unfoundedNumbers: [30, 30],
  fakeExperience: [50, 50],
  repeatsPastPost: [10, 30],
}

export function computeViralScore(sub = {}, penalties = []) {
  let base = 0
  const breakdown = {}
  for (const [key, max] of Object.entries(VIRAL_WEIGHTS)) {
    const ratio = clamp(Number(sub[key] ?? 0), 0, 1)
    const points = Math.round(ratio * max)
    breakdown[key] = points
    base += points
  }

  let penaltyTotal = 0
  const appliedPenalties = penalties.map((p) => {
    const [min, max] = PENALTY_RANGES[p.type] ?? [0, 0]
    const amount = clamp(Number(p.amount ?? max), min, max)
    penaltyTotal += amount
    return { ...p, amount }
  })

  const total = clamp(Math.round(base - penaltyTotal), 0, 100)
  return { total, base, penaltyTotal, breakdown, appliedPenalties }
}

export function scoreTier(score) {
  if (score >= 85) return { label: '강력 추천', tone: 'good' }
  if (score >= 70) return { label: '괜찮음', tone: 'good' }
  if (score >= 50) return { label: '보완 필요', tone: 'warn' }
  return { label: '재생성 권장', tone: 'bad' }
}
