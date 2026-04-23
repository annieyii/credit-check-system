import { useState, useCallback } from "react"
import axios from "axios"

export type ErrorType = "format" | "server" | "network" | "unknown" | ""

export function useErrorHandler() {
  const [error, setError] = useState<string | null>(null)
  const [errorType, setErrorType] = useState<ErrorType>("")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const clearError = useCallback(() => {
    setError(null)
    setErrorType("")
  }, [])

  const submitToApi = useCallback(async (file: File) => {
    setIsLoading(true)
    setError(null)
    setErrorType("")
    setResult(null)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const res = await axios.post("http://127.0.0.1:8000/upload_file", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      setResult(res.data)

    } catch (err: any) {
      if (err.response) {
        const status = err.response.status
        const detail = err.response.data?.detail || "請確認 JSON 內容是否正確"

        if (status === 400) {
          setErrorType("format")
          setError(`JSON 格式錯誤：${detail}`)
        } else if (status === 404) {
          setErrorType("server")
          setError("找不到伺服器，請確認 API 網址是否正確")
        } else if (status === 422) {
          setErrorType("format")
          setError(`資料驗證失敗：${detail}`)
        } else if (status === 500) {
          setErrorType("server")
          setError("伺服器內部錯誤，請稍後再試")
        } else {
          setErrorType("server")
          setError(`伺服器錯誤（${status}）：${detail}`)
        }
      } else if (err.request) {
        setErrorType("network")
        setError("無法連線到伺服器，請確認後端是否正常運行")
      } else {
        setErrorType("unknown")
        setError(`發生未知錯誤：${err.message}`)
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    error,
    errorType,
    isLoading,
    result,
    clearError,
    submitToApi,
    setError,      
    setErrorType,
  }
}
