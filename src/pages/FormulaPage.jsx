import { useMemo } from 'react'
import { getViralType, LENGTHS } from '../data/viralTypes.js'
import { aggregateByViralType, aggregateByLength, getPosts, getTemplates } from '../lib/store.js'
import { Card, SectionTitle } from '../components/ui.jsx'

const MIN_POSTS_FOR_CONFIDENCE = 5

export default function FormulaPage() {
  const posts = useMemo(() => getPosts(), [])
  const byType = useMemo(() => aggregateByViralType(), [])
  const byLength = useMemo(() => aggregateByLength(), [])
  const templates = useMemo(() => getTemplates(), [])

  const postsWithStats = posts.filter((p) => p.views > 0)
  const hasEnoughData = postsWithStats.length >= MIN_POSTS_FOR_CONFIDENCE
  const topType = byType[0]
  const topLength = byLength[0]

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <SectionTitle
          title="바이럴 공식"
          desc="인터넷의 '정답'이 아니라, 내 계정에서 실제로 통했던 패턴을 학습합니다."
        />
        {postsWithStats.length === 0 ? (
          <p className="text-sm text-[var(--text-dim)]">
            아직 성과가 기록된 게시물이 없습니다. '내 성과' 탭에서 게시 후 조회수·좋아요·답글 수를 입력하면 여기에 패턴이 쌓입니다.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {!hasEnoughData && (
              <p className="text-xs text-[var(--warn)] bg-[var(--warn-bg)] rounded-md px-3 py-2">
                아직 데이터가 {postsWithStats.length}개뿐이라 패턴이 확정적이지 않습니다. 최소 {MIN_POSTS_FOR_CONFIDENCE}개 이상 쌓이면 더 신뢰할 수 있어요.
              </p>
            )}
            {topType && topLength && (
              <p className="text-sm leading-relaxed">
                지금까지의 기록을 보면{' '}
                <b className="text-[var(--accent)]">
                  {getViralType(topType.viralTypeId)?.emoji} {getViralType(topType.viralTypeId)?.name}
                </b>{' '}
                구조 +{' '}
                <b className="text-[var(--accent)]">{LENGTHS.find((l) => l.id === topLength.length)?.label}</b>{' '}
                길이 조합에서 평균 참여도가 가장 높았습니다 (평균 조회수 {Math.round(topType.avgViews).toLocaleString()}).
              </p>
            )}
          </div>
        )}
      </Card>

      {byType.length > 0 && (
        <Card>
          <SectionTitle title="바이럴 구조별 성과" />
          <RankTable
            rows={byType.map((r) => ({
              key: r.viralTypeId,
              label: `${getViralType(r.viralTypeId)?.emoji ?? ''} ${getViralType(r.viralTypeId)?.name ?? r.viralTypeId}`,
              count: r.count,
              avgViews: r.avgViews,
              avgEngagement: r.avgEngagement,
            }))}
          />
        </Card>
      )}

      {byLength.length > 0 && (
        <Card>
          <SectionTitle title="길이별 성과" />
          <RankTable
            rows={byLength.map((r) => ({
              key: r.length,
              label: LENGTHS.find((l) => l.id === r.length)?.label ?? r.length,
              count: r.count,
              avgViews: r.avgViews,
              avgEngagement: r.avgEngagement,
            }))}
          />
        </Card>
      )}

      <Card>
        <SectionTitle
          title={`저장된 구조 템플릿 (${templates.length})`}
          desc="'터진 글 분석' 탭에서 추출한, 재사용 가능한 구조 패턴 DB입니다."
        />
        {templates.length === 0 ? (
          <p className="text-sm text-[var(--text-dim)]">아직 저장된 구조 템플릿이 없습니다.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {templates.map((t) => (
              <div key={t.id} className="border border-[var(--border)] rounded-lg p-3 text-sm">
                <div className="text-xs text-[var(--text-dim)] mb-1">
                  {getViralType(t.matchedViralType)?.name ?? t.matchedViralType} · Conversation Gap {t.conversationGap?.level}
                </div>
                <div className="font-mono text-xs">{t.structureTemplate}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

function RankTable({ rows }) {
  const maxEngagement = Math.max(...rows.map((r) => r.avgEngagement), 1)
  return (
    <div className="flex flex-col gap-2">
      {rows.map((r, i) => (
        <div key={r.key} className="flex items-center gap-3">
          <span className="text-xs w-5 text-[var(--text-dim)]">{i + 1}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="truncate">{r.label}</span>
              <span className="text-xs text-[var(--text-dim)] shrink-0">
                {r.count}개 · 평균 {Math.round(r.avgViews).toLocaleString()} 조회
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
              <div
                className="h-full bg-[var(--accent)] rounded-full"
                style={{ width: `${Math.max(4, (r.avgEngagement / maxEngagement) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
