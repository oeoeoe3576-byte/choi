import { useState } from 'react'
import { getViralType, LENGTHS, CONVERSATION_TRIGGER_STYLES, ANALYSIS_FACTORS } from '../data/viralTypes.js'
import { analyzeTopic, generateHooks, generateBody, adjustBody } from '../lib/api.js'
import { scoreTier } from '../lib/scoring.js'
import { addPost } from '../lib/store.js'
import { Button, Card, ErrorBanner, ScorePill, SectionTitle, Spinner } from '../components/ui.jsx'

const VIRAL_SUB_LABELS = {
  firstLine: '첫 문장',
  curiosity: '호기심',
  empathy: '공감',
  opinionPotential: '의견 발생 가능성',
  specificity: '구체성',
  infoOrExperienceValue: '정보/경험 가치',
  naturalness: '자연스러움',
  topicFit: '계정 주제 적합도',
}

const ADJUST_BUTTONS = [
  { id: 'stronger', label: '더 세게' },
  { id: 'softer', label: '덜 자극적으로' },
  { id: 'natural', label: '더 자연스럽게' },
]

export default function ComposePage() {
  const [topicText, setTopicText] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [selectedTypeId, setSelectedTypeId] = useState(null)
  const [hooks, setHooks] = useState([])
  const [shownHookTexts, setShownHookTexts] = useState([])
  const [selectedHook, setSelectedHook] = useState(null)
  const [length, setLength] = useState('medium')
  const [ctaStyle, setCtaStyle] = useState('strong')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)

  async function handleAnalyze() {
    if (!topicText.trim()) return
    setError(null)
    setLoading('analyze')
    setAnalysis(null)
    setSelectedTypeId(null)
    setHooks([])
    setSelectedHook(null)
    setResult(null)
    try {
      const res = await analyzeTopic(topicText)
      setAnalysis(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(null)
    }
  }

  async function handleSelectType(typeId) {
    setSelectedTypeId(typeId)
    setSelectedHook(null)
    setResult(null)
    setError(null)
    setLoading('hooks')
    try {
      const res = await generateHooks(topicText, typeId)
      const top3 = res.hooks.slice(0, 3)
      setHooks(top3)
      setShownHookTexts(res.hooks.map((h) => h.text))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(null)
    }
  }

  async function handleRegenerateHooks() {
    setError(null)
    setLoading('hooks')
    try {
      const res = await generateHooks(topicText, selectedTypeId, shownHookTexts)
      const top3 = res.hooks.slice(0, 3)
      setHooks(top3)
      setShownHookTexts((prev) => [...prev, ...res.hooks.map((h) => h.text)])
      setSelectedHook(null)
      setResult(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(null)
    }
  }

  function handleSelectHook(hook) {
    setSelectedHook(hook)
    setResult(null)
    setSaved(false)
  }

  async function handleGenerateBody() {
    setError(null)
    setLoading('body')
    setSaved(false)
    try {
      const res = await generateBody({
        topicText,
        viralTypeId: selectedTypeId,
        hookText: selectedHook.text,
        length,
        ctaStyleId: ctaStyle,
        factors: analysis.factors,
        mainTopic: analysis.mainTopic,
        subTopic: analysis.subTopic,
      })
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(null)
    }
  }

  async function handleAdjust(instruction) {
    if (!result) return
    setError(null)
    setLoading('adjust')
    setSaved(false)
    try {
      const res = await adjustBody({
        topicText,
        viralTypeId: selectedTypeId,
        hookText: selectedHook.text,
        previousBody: result.body,
        length,
        instruction,
      })
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(null)
    }
  }

  function handleSaveDraft() {
    addPost({
      viralTypeId: selectedTypeId,
      length,
      hookText: selectedHook.text,
      body: result.body,
    })
    setSaved(true)
  }

  function handleCopy() {
    navigator.clipboard?.writeText(result.body).catch(() => {})
  }

  const selectedType = selectedTypeId ? getViralType(selectedTypeId) : null

  return (
    <div className="flex flex-col gap-6">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {/* Step 1: 소재 입력 */}
      <Card>
        <SectionTitle step={1} title="오늘 쓰고 싶은 내용" desc="글을 바로 쓰지 않습니다. 먼저 이 소재가 왜 흥미로운지부터 분석합니다." />
        <textarea
          value={topicText}
          onChange={(e) => setTopicText(e.target.value)}
          placeholder="예: 신혼여행 다녀오면서 느낀 점 쓰고 싶음. 생각보다 숙소에 돈 많이 쓸 필요 없는 것 같음."
          rows={4}
          className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
        />
        <div className="mt-3 flex justify-end">
          <Button onClick={handleAnalyze} disabled={loading === 'analyze' || !topicText.trim()}>
            {loading === 'analyze' && <Spinner />} 분석하기
          </Button>
        </div>
      </Card>

      {/* Step 2: 분석 결과 + 추천 구조 */}
      {analysis && (
        <Card>
          <SectionTitle step={2} title="추천 구조" desc={analysis.summary} />
          <div className="flex flex-wrap gap-1.5 mb-3">
            {ANALYSIS_FACTORS.map((f) => (
              <span key={f.key} className="text-xs px-2 py-1 rounded-md bg-[var(--surface-2)] text-[var(--text-dim)]">
                {f.label} {analysis.factors?.[f.key] ?? '-'}
              </span>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {analysis.top3.map((t, i) => (
              <button
                key={t.id}
                onClick={() => handleSelectType(t.id)}
                className={`text-left rounded-lg border p-3 transition-colors ${
                  selectedTypeId === t.id
                    ? 'border-[var(--accent)] bg-[var(--accent-bg)]'
                    : 'border-[var(--border)] hover:border-[var(--accent)]/50'
                }`}
              >
                <div className="text-xs text-[var(--text-dim)] mb-1">{['🥇', '🥈', '🥉'][i]} {t.fit}점</div>
                <div className="font-semibold text-sm">{t.emoji} {t.name}</div>
                <div className="text-xs text-[var(--text-dim)] mt-1">{t.oneLiner}</div>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Step 3: 훅 후보 */}
      {selectedTypeId && (
        <Card>
          <SectionTitle step={3} title="후킹 후보" desc={`${selectedType.name} 구조로 뽑은 첫 문장 후보 중 상위 3개`} />
          {loading === 'hooks' && !hooks.length ? (
            <div className="flex items-center gap-2 text-sm text-[var(--text-dim)] py-6 justify-center">
              <Spinner /> 훅 생성 중...
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {hooks.map((h, i) => {
                const tier = scoreTier(h.hookScore.total)
                return (
                  <button
                    key={h.text + i}
                    onClick={() => handleSelectHook(h)}
                    className={`text-left rounded-lg border p-3 transition-colors ${
                      selectedHook?.text === h.text
                        ? 'border-[var(--accent)] bg-[var(--accent-bg)]'
                        : 'border-[var(--border)] hover:border-[var(--accent)]/50'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-mono text-[var(--text-dim)]">{String.fromCharCode(65 + i)}</span>
                      <ScorePill score={h.hookScore.total} tone={tier.tone} />
                    </div>
                    <p className="text-sm whitespace-pre-line">{h.text}</p>
                  </button>
                )
              })}
              <div className="flex justify-end mt-1">
                <Button variant="ghost" onClick={handleRegenerateHooks} disabled={loading === 'hooks'}>
                  {loading === 'hooks' && <Spinner />} 다른 훅 보기
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Step 4: 길이/CTA 선택 + 본문 생성 */}
      {selectedHook && (
        <Card>
          <SectionTitle step={4} title="본문 만들기" />
          <div className="flex flex-wrap gap-4 mb-4">
            <div>
              <div className="text-xs text-[var(--text-dim)] mb-1.5">길이</div>
              <div className="flex gap-1.5">
                {LENGTHS.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => setLength(l.id)}
                    className={`px-2.5 py-1.5 rounded-md text-xs font-medium border ${
                      length === l.id
                        ? 'border-[var(--accent)] bg-[var(--accent-bg)] text-[var(--accent)]'
                        : 'border-[var(--border)] text-[var(--text-dim)]'
                    }`}
                    title={l.desc}
                  >
                    {l.label} · {l.lines}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--text-dim)] mb-1.5">Conversation Trigger</div>
              <select
                value={ctaStyle}
                onChange={(e) => setCtaStyle(e.target.value)}
                className="px-2.5 py-1.5 rounded-md text-xs border border-[var(--border)] bg-[var(--surface-2)]"
              >
                {CONVERSATION_TRIGGER_STYLES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button onClick={handleGenerateBody} disabled={loading === 'body'}>
            {loading === 'body' && <Spinner />} 본문 생성
          </Button>
        </Card>
      )}

      {/* Step 5: 결과 */}
      {result && (
        <Card>
          <SectionTitle step={5} title="완성된 게시물" />
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <ScorePill score={result.viralScore.total} tone={scoreTier(result.viralScore.total).tone} label="Viral Score" />
            <ScorePill
              score={result.hookPayoff.score}
              tone={result.hookPayoff.passesThreshold ? 'good' : 'bad'}
              label="Hook-Payoff"
            />
            {result.aiSmell.hits.length > 0 && (
              <ScorePill score={result.aiSmell.hits.length} tone="warn" label="AI 말투 감지" />
            )}
          </div>

          <div className="whitespace-pre-line text-sm bg-[var(--surface-2)] rounded-lg p-4 border border-[var(--border)] leading-relaxed">
            {result.body}
          </div>

          <details className="mt-3">
            <summary className="text-xs text-[var(--text-dim)] cursor-pointer">세부 점수 보기</summary>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {Object.entries(result.viralScore.breakdown).map(([key, val]) => (
                <span key={key} className="text-xs px-2 py-1 rounded-md bg-[var(--surface-2)] text-[var(--text-dim)]">
                  {VIRAL_SUB_LABELS[key] ?? key} {val}
                </span>
              ))}
            </div>
            {result.viralScore.appliedPenalties.length > 0 && (
              <ul className="mt-2 text-xs text-[var(--bad)] list-disc list-inside">
                {result.viralScore.appliedPenalties.map((p, i) => (
                  <li key={i}>
                    -{p.amount}점 · {p.reason || p.type}
                  </li>
                ))}
              </ul>
            )}
          </details>

          <div className="flex flex-wrap gap-1.5 mt-4">
            {ADJUST_BUTTONS.map((b) => (
              <Button key={b.id} variant="outline" onClick={() => handleAdjust(b.id)} disabled={loading === 'adjust'}>
                {loading === 'adjust' && <Spinner />} {b.label}
              </Button>
            ))}
            <Button variant="outline" onClick={handleRegenerateHooks} disabled={loading === 'hooks'}>
              다른 훅
            </Button>
          </div>

          <div className="flex gap-2 mt-4 pt-4 border-t border-[var(--border)]">
            <Button onClick={handleCopy}>복사하기</Button>
            <Button variant="secondary" onClick={handleSaveDraft} disabled={saved}>
              {saved ? '내 성과에 저장됨 ✓' : '내 성과에 초안으로 저장'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
