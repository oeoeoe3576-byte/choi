import { useState } from 'react'
import { getViralType } from '../data/viralTypes.js'
import { reverseEngineer } from '../lib/api.js'
import { addTemplate, getTemplates, deleteTemplate } from '../lib/store.js'
import { Button, Card, ErrorBanner, SectionTitle, Spinner } from '../components/ui.jsx'

const GAP_TONE = { 낮음: 'bad', 중간: 'warn', 높음: 'good' }

export default function ReverseEngineerPage() {
  const [pastedText, setPastedText] = useState('')
  const [sourceNote, setSourceNote] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [templates, setTemplates] = useState(getTemplates())
  const [savedId, setSavedId] = useState(null)

  async function handleAnalyze() {
    if (!pastedText.trim()) return
    setError(null)
    setLoading(true)
    setResult(null)
    try {
      const res = await reverseEngineer(pastedText)
      setResult(res)
      setSavedId(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSave() {
    if (!result) return
    const record = addTemplate({ ...result, sourceNote })
    setTemplates(getTemplates())
    setSavedId(record.id)
  }

  function handleDelete(id) {
    setTemplates(deleteTemplate(id))
  }

  return (
    <div className="flex flex-col gap-6">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      <Card>
        <SectionTitle
          step={null}
          title="터진 글 분석"
          desc="반응이 좋았던 게시물을 붙여넣으면 구조만 추출합니다. 문장을 그대로 베끼지 않고 '바이럴 공식' 탭에 재사용 가능한 템플릿으로 저장됩니다."
        />
        <textarea
          value={pastedText}
          onChange={(e) => setPastedText(e.target.value)}
          placeholder="반응이 좋았던 Threads 게시물 원문을 붙여넣으세요."
          rows={6}
          className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
        />
        <input
          value={sourceNote}
          onChange={(e) => setSourceNote(e.target.value)}
          placeholder="출처 메모 (선택, 예: @계정명 / 2026-08 게시물)"
          className="mt-2 w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs outline-none focus:border-[var(--accent)]"
        />
        <div className="mt-3 flex justify-end">
          <Button onClick={handleAnalyze} disabled={loading || !pastedText.trim()}>
            {loading && <Spinner />} 구조 분석하기
          </Button>
        </div>
      </Card>

      {result && (
        <Card>
          <SectionTitle title="분석 결과" />
          <div className="grid gap-3 sm:grid-cols-2 text-sm">
            <Field label="Hook 기법">{result.hook}</Field>
            <Field label="심리 기제">{result.hookMechanism}</Field>
            <Field label="자극하는 감정">{result.emotion}</Field>
            <Field label="가장 가까운 유형">
              {getViralType(result.matchedViralType)?.emoji} {getViralType(result.matchedViralType)?.name ?? result.matchedViralType}
            </Field>
          </div>
          <Field label="전개 구조 (Mechanism)" className="mt-3">
            {result.mechanism}
          </Field>
          <Field label="Conversation Gap" className="mt-3">
            <span
              className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold mr-2 ${
                { good: 'text-[var(--good)] bg-[var(--good-bg)]', warn: 'text-[var(--warn)] bg-[var(--warn-bg)]', bad: 'text-[var(--bad)] bg-[var(--bad-bg)]' }[
                  GAP_TONE[result.conversationGap?.level] ?? 'warn'
                ]
              }`}
            >
              {result.conversationGap?.level}
            </span>
            {result.conversationGap?.reason}
          </Field>
          <Field label="재사용 가능한 구조 템플릿" className="mt-3">
            <span className="font-mono text-xs bg-[var(--surface-2)] rounded px-2 py-1 inline-block">
              {result.structureTemplate}
            </span>
          </Field>
          <div className="mt-4">
            <Button variant="secondary" onClick={handleSave} disabled={savedId != null}>
              {savedId ? '바이럴 공식에 저장됨 ✓' : '이 구조를 바이럴 공식에 저장'}
            </Button>
          </div>
        </Card>
      )}

      {templates.length > 0 && (
        <Card>
          <SectionTitle title={`저장된 구조 템플릿 (${templates.length})`} />
          <div className="flex flex-col gap-2">
            {templates.map((t) => (
              <div key={t.id} className="border border-[var(--border)] rounded-lg p-3 text-sm flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs text-[var(--text-dim)] mb-1">
                    {getViralType(t.matchedViralType)?.name ?? t.matchedViralType} {t.sourceNote && `· ${t.sourceNote}`}
                  </div>
                  <div className="font-mono text-xs">{t.structureTemplate}</div>
                </div>
                <button onClick={() => handleDelete(t.id)} className="text-xs text-[var(--text-dim)] hover:text-[var(--bad)] shrink-0">
                  삭제
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      <div className="text-xs text-[var(--text-dim)] mb-0.5">{label}</div>
      <div>{children}</div>
    </div>
  )
}
