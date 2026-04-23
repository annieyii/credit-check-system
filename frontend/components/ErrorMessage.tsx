import { ErrorType } from "@/hooks/useErrorHandler"

interface Props {
  message: string | null
  type: ErrorType
  onClose: () => void
}

const config = {
  format:  { icon: "⚠️", className: "bg-yellow-50 border-yellow-300 text-yellow-800" },
  server:  { icon: "🔴", className: "bg-red-50 border-red-300 text-red-800" },
  network: { icon: "🔌", className: "bg-purple-50 border-purple-300 text-purple-800" },
  unknown: { icon: "❓", className: "bg-gray-100 border-gray-300 text-gray-800" },
}

export default function ErrorMessage({ message, type, onClose }: Props) {
  if (!message) return null

  const style = config[type as keyof typeof config] ?? config.unknown

  return (
    <div
      role="alert"
      className={`flex items-start gap-2 mt-3 p-3 rounded-lg border text-sm ${style.className}`}
    >
      <span>{style.icon}</span>
      <span className="flex-1">{message}</span>
      <button
        onClick={onClose}
        aria-label="關閉錯誤訊息"
        className="opacity-60 hover:opacity-100 transition-opacity"
      >
        ✕
      </button>
    </div>
  )
}
