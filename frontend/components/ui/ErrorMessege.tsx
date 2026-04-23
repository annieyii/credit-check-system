type ErrorType = 'format' | 'server' | 'network' | 'unknown' | ''

interface Props {
  message: string
  type: ErrorType
  onClose: () => void
}

const config = {
  format:  { icon: '⚠️', bg: '#fef9c3', border: '#facc15', color: '#713f12' },
  server:  { icon: '🔴', bg: '#fee2e2', border: '#f87171', color: '#7f1d1d' },
  network: { icon: '🔌', bg: '#ede9fe', border: '#a78bfa', color: '#3b0764' },
  unknown: { icon: '❓', bg: '#f3f4f6', border: '#d1d5db', color: '#111827' },
}

export default function ErrorMessage({ message, type, onClose }: Props) {
  if (!message) return null

  const style = config[type as keyof typeof config] ?? config.unknown

  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        padding: '12px 16px',
        borderRadius: '8px',
        border: `1px solid ${style.border}`,
        backgroundColor: style.bg,
        color: style.color,
        marginTop: '16px',
        fontSize: '14px',
        lineHeight: '1.5',
      }}
    >
      <span>{style.icon}</span>
      <span style={{ flex: 1 }}>{message}</span>
      <button
        onClick={onClose}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          fontSize: '14px',
          color: 'inherit',
          opacity: 0.6,
          padding: 0,
        }}
        aria-label="關閉錯誤訊息"
      >
        ✕
      </button>
    </div>
  )
}