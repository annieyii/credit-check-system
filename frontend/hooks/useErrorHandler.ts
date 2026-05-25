import { useState, useCallback } from "react"
import axios from "axios"

export type ErrorType = "format" | "server" | "network" | "unknown" | ""

export interface GraduationResult {
  dept_name: string
  applicable_year: string
  summary: {
    total_credits_earned: number
    required_credits_earned: number
    required_credits_needed: number
    pe_credits_earned: number
    pe_credits_needed: number
    general_credits_earned: number
    general_credits_needed: number
    elective_credits_earned: number
    elective_credits_needed: number
  }
  required_courses: {
    passed: string[]
    missing: string[]
    main_major?: {
      dept_name: string
      year: string
      passed: string[]
      missing: string[]
      credits_earned: number
      credits_needed: number
    }
    double_major?: {
      dept_name: string
      year: string
      passed: string[]
      missing: string[]
      credits_earned: number
      credits_needed: number
    } | null
  }
  general_education?: {
    credits_earned: number
    credits_needed: number
    passed: boolean
    by_category: Record<string, number>
    raw_by_category?: Record<string, number>
    limits?: Record<string, [number, number]>
    core_count?: number
    core_required?: number
    core_domains_taken?: string[]
    core_courses?: Array<{
      courseCode: string
      courseName: string
      credits: number
      category: string
      source: "regular" | "waived"
    }>
    is_info_dept?: boolean
    info_warning_courses?: Array<{
      courseCode: string
      courseName: string
      credits: number
    }>
    violations?: string[]
    taken_courses?: Array<{
      courseCode: string
      courseName: string
      credits: string | number
      category: string
      source: "regular" | "waived"
    }>
  }
  physical_education?: {
    credits_earned: number
    credits_needed: number
    passed: boolean
    courses: string[]
    course_details?: Array<{
      courseCode: string
      courseName: string
      credits: string | number
      grade: string
      semester: string
      academicYear: string
      status: "通過" | "重複不計" | "超修不計"
    }>
    senior_warning?: boolean
    senior_warning_semesters?: string[]
  }
  elective?: {
    credits_earned: number
    credits_needed: number
    passed: boolean
    in_dept_credits: number
    out_dept_credits: number
    in_dept_courses?: Array<{
      courseCode: string
      courseName: string
      credits: string | number
      grade: string
    }>
    out_dept_courses?: Array<{
      courseCode: string
      courseName: string
      credits: string | number
      grade: string
    }>
  }
  minor?: {
    passed: string[]
    missing: string[]
    credits_earned: number
    credits_needed: number
  }
  is_eligible_to_graduate: boolean
}

export function useErrorHandler() {
  const [error, setError] = useState<string | null>(null)
  const [errorType, setErrorType] = useState<ErrorType>("")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<GraduationResult | null>(null)

  const clearError = useCallback(() => {
    setError(null)
    setErrorType("")
  }, [])

  const clearResult = useCallback(() => {
    setResult(null)
  }, [])

  const submitToApi = useCallback(async (parsed: object, role: string) => {
    setIsLoading(true)
    setError(null)
    setErrorType("")
    setResult(null)

    try {
      const payload = { role, data: parsed }
      console.log("Request payload size:", JSON.stringify(payload).length, "bytes")
      const res = await axios.post("http://127.0.0.1:8000/api/v1/analyze", payload, {
        timeout: 30000,
      })
      setResult(res.data)

    } catch (err: unknown) {
      console.error("API request error:", err)
      if (axios.isAxiosError(err) && err.response) {
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
      } else if (axios.isAxiosError(err) && err.request) {
        setErrorType("network")
        setError("無法連線到伺服器，請確認前端 API 是否正常運行")
      } else {
        setErrorType("unknown")
        setError(`發生未知錯誤：${err instanceof Error ? err.message : "未知錯誤"}`)
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
    clearResult,
    submitToApi,
    setError,      
    setErrorType,
  }
}
