export function Card({ className = '', children, ...props }) {
  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}

export function Button({ variant = 'primary', className = '', children, ...props }) {
  const base = 'inline-flex items-center justify-center gap-1.5 rounded-lg text-sm font-medium px-3.5 py-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-[var(--accent)] text-white hover:bg-[var(--accent-2)]',
    secondary: 'bg-[var(--surface-2)] text-[var(--text)] hover:bg-[var(--border)]',
    ghost: 'text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]',
    outline: 'border border-[var(--border)] text-[var(--text)] hover:bg-[var(--surface-2)]',
  }
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Spinner({ className = '' }) {
  return (
    <span
      className={`inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin ${className}`}
    />
  )
}

export function SectionTitle({ step, title, desc }) {
  return (
    <div className="mb-3">
      <div className="flex items-center gap-2">
        {step != null && (
          <span className="w-5 h-5 flex items-center justify-center rounded-full bg-[var(--accent-bg)] text-[var(--accent)] text-xs font-bold">
            {step}
          </span>
        )}
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      {desc && <p className="text-xs text-[var(--text-dim)] mt-1">{desc}</p>}
    </div>
  )
}

const TONE_CLASSES = {
  good: 'text-[var(--good)] bg-[var(--good-bg)]',
  warn: 'text-[var(--warn)] bg-[var(--warn-bg)]',
  bad: 'text-[var(--bad)] bg-[var(--bad-bg)]',
}

export function ScorePill({ score, tone = 'good', label }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${TONE_CLASSES[tone]}`}>
      {label ? `${label} ` : ''}
      {score}
    </span>
  )
}

export function ErrorBanner({ message, onDismiss }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-2 bg-[var(--bad-bg)] text-[var(--bad)] text-sm rounded-lg px-3 py-2 border border-[var(--bad-border)]">
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="font-bold leading-none">
          ×
        </button>
      )}
    </div>
  )
}
