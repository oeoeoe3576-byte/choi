import { useState } from 'react'
import ComposePage from './pages/ComposePage.jsx'
import ReverseEngineerPage from './pages/ReverseEngineerPage.jsx'
import PerformancePage from './pages/PerformancePage.jsx'
import FormulaPage from './pages/FormulaPage.jsx'

const TABS = [
  { id: 'compose', label: '글 만들기', emoji: '✍️', Component: ComposePage },
  { id: 'reverse', label: '터진 글 분석', emoji: '🔍', Component: ReverseEngineerPage },
  { id: 'performance', label: '내 성과', emoji: '📊', Component: PerformancePage },
  { id: 'formula', label: '바이럴 공식', emoji: '🧪', Component: FormulaPage },
]

export default function App() {
  const [tabId, setTabId] = useState('compose')
  const ActiveTab = TABS.find((t) => t.id === tabId)?.Component ?? ComposePage

  return (
    <div className="min-h-svh flex flex-col">
      <header className="border-b border-[var(--border)] sticky top-0 bg-[var(--bg)]/95 backdrop-blur z-10">
        <div className="max-w-3xl mx-auto px-4 pt-4">
          <h1 className="text-lg font-semibold tracking-tight">Threads 바이럴 엔진</h1>
          <p className="text-xs text-[var(--text-dim)] mt-0.5">
            소재를 대신 써주는 게 아니라, 터질 구조를 찾아내는 엔진
          </p>
        </div>
        <nav className="max-w-3xl mx-auto px-4 mt-3 flex gap-1 overflow-x-auto scrollbar-thin">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTabId(t.id)}
              className={`px-3 py-2 text-sm font-medium rounded-t-lg border-b-2 whitespace-nowrap transition-colors ${
                tabId === t.id
                  ? 'border-[var(--accent)] text-[var(--text)]'
                  : 'border-transparent text-[var(--text-dim)] hover:text-[var(--text)]'
              }`}
            >
              <span className="mr-1">{t.emoji}</span>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-6">
        <ActiveTab />
      </main>

      <footer className="text-center text-xs text-[var(--text-dim)] py-6 px-4">
        내 계정 데이터로 학습하는 도구입니다 · 하루 대량 생성보다 좋은 글 하나 + 댓글 대화를 권장합니다
      </footer>
    </div>
  )
}
