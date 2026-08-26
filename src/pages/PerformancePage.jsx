import { useState } from 'react'
import { VIRAL_TYPES, LENGTHS, getViralType } from '../data/viralTypes.js'
import { getPosts, addPost, updatePost, deletePost, engagementScore } from '../lib/store.js'
import { Button, Card, SectionTitle } from '../components/ui.jsx'

const STAT_FIELDS = [
  { key: 'views', label: '조회수' },
  { key: 'likes', label: '좋아요' },
  { key: 'replies', label: '답글' },
  { key: 'reposts', label: '재게시' },
  { key: 'quotes', label: '인용' },
  { key: 'followerDelta', label: '팔로워 증가' },
]

const EMPTY_FORM = { viralTypeId: '', length: 'medium', hookText: '', views: '', likes: '', replies: '', reposts: '', quotes: '', followerDelta: '' }

export default function PerformancePage() {
  const [posts, setPosts] = useState(getPosts())
  const [form, setForm] = useState(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)

  function handleStatChange(id, key, value) {
    const patch = { [key]: Number(value) || 0 }
    setPosts(updatePost(id, patch))
  }

  function handleDelete(id) {
    setPosts(deletePost(id))
  }

  function handleAddManual() {
    if (!form.viralTypeId || !form.hookText.trim()) return
    addPost(form)
    setPosts(getPosts())
    setForm(EMPTY_FORM)
    setShowForm(false)
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex items-center justify-between">
          <SectionTitle
            title="내 성과"
            desc="Threads에 게시한 뒤 실제 수치를 채워 넣으세요. 이 데이터가 '바이럴 공식' 탭의 학습 근거가 됩니다."
          />
          <Button variant="secondary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? '닫기' : '+ 직접 기록 추가'}
          </Button>
        </div>

        {showForm && (
          <div className="border border-[var(--border)] rounded-lg p-3 mb-3 flex flex-col gap-2">
            <div className="flex gap-2 flex-wrap">
              <select
                value={form.viralTypeId}
                onChange={(e) => setForm((f) => ({ ...f, viralTypeId: e.target.value }))}
                className="px-2.5 py-1.5 rounded-md text-xs border border-[var(--border)] bg-[var(--surface-2)]"
              >
                <option value="">바이럴 구조 선택</option>
                {VIRAL_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.emoji} {t.name}
                  </option>
                ))}
              </select>
              <select
                value={form.length}
                onChange={(e) => setForm((f) => ({ ...f, length: e.target.value }))}
                className="px-2.5 py-1.5 rounded-md text-xs border border-[var(--border)] bg-[var(--surface-2)]"
              >
                {LENGTHS.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
            <input
              value={form.hookText}
              onChange={(e) => setForm((f) => ({ ...f, hookText: e.target.value }))}
              placeholder="첫 문장(훅)"
              className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1.5 text-xs outline-none"
            />
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
              {STAT_FIELDS.map((s) => (
                <input
                  key={s.key}
                  type="number"
                  value={form[s.key]}
                  onChange={(e) => setForm((f) => ({ ...f, [s.key]: e.target.value }))}
                  placeholder={s.label}
                  className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 text-xs outline-none"
                />
              ))}
            </div>
            <div className="flex justify-end">
              <Button onClick={handleAddManual} disabled={!form.viralTypeId || !form.hookText.trim()}>
                저장
              </Button>
            </div>
          </div>
        )}
      </Card>

      {posts.length === 0 ? (
        <Card className="text-center text-sm text-[var(--text-dim)] py-10">
          아직 기록된 게시물이 없습니다. '글 만들기' 탭에서 만든 글을 저장하거나 직접 기록을 추가해보세요.
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {posts.map((p) => {
            const type = getViralType(p.viralTypeId)
            return (
              <Card key={p.id}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <div className="text-xs text-[var(--text-dim)]">
                      {type ? `${type.emoji} ${type.name}` : '유형 미지정'} · {p.length?.toUpperCase()} ·{' '}
                      {new Date(p.createdAt).toLocaleDateString('ko-KR')}
                    </div>
                    <p className="text-sm mt-1 whitespace-pre-line">{p.hookText}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-semibold text-[var(--accent)]">
                      참여도 {engagementScore(p).toFixed(1)}
                    </span>
                    <button onClick={() => handleDelete(p.id)} className="text-xs text-[var(--text-dim)] hover:text-[var(--bad)]">
                      삭제
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
                  {STAT_FIELDS.map((s) => (
                    <label key={s.key} className="text-xs">
                      <span className="block text-[var(--text-dim)] mb-0.5">{s.label}</span>
                      <input
                        type="number"
                        value={p[s.key]}
                        onChange={(e) => handleStatChange(p.id, s.key, e.target.value)}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 outline-none"
                      />
                    </label>
                  ))}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
