"use client"

import { useState, useCallback, useRef } from "react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, FileJson, X, Loader2 } from "lucide-react"
import { useErrorHandler } from "@/hooks/useErrorHandler"
import ErrorMessage from "@/components/ErrorMessage"
import GraduationResult from "@/components/GraduationResult"
import { z } from "zod"

const coursePlanSchema = z
  .object({
    liberalTotal: z.string(),
    programName: z.string(),
    requiredPoint: z.string(),
    groupPoint: z.string(),
    programRemark: z.string(),
    groupRemark: z.string(),
    liberalChinese: z.string(),
    commonPhysical: z.string(),
    liberalGeneral: z.string(),
    commonPhysicalCount: z.string(),
    requiredRemark: z.string(),
    graduationCredit: z.string(),
    commonLanguage: z.string(),
    coursePlanTimestamp: z.string(),
    liberalEnglish: z.string(),
    commonLanguageCount: z.string(),
    coursePlanSchyy: z.string(),
  })
  .passthrough()

const aboutMeSchema = z
  .object({
    addMjrYN: z.string(),
    studentNumber: z.string(),
    englishName: z.string(),
    chineseName: z.string(),
    minor1: z.string(),
    registerMajor: z.string(),
    minor2: z.string(),
    instructor: z.string(),
    doubleMajor: z.string(),
    thesisTitle: z.string(),
    registerMinor: z.string(),
    program: z.string(),
    studentIdentity: z.string(),
    studentIdentity2: z.string(),
    registrationStatus: z.string(),
    collegeEnglishExemption: z.string(),
    registerOtherProgramList: z.array(z.unknown()),
    registerDoubleMajor: z.string(),
    departmentProgramGrade: z.string(),
  })
  .passthrough()

const enrollmentHistoryItemSchema = z.object({
  academicYearSemester: z.string(),
  registerStatus: z.string(),
  gradeName: z.string(),
})

const averageScoreItemSchema = z.object({
  academicYear: z.string(),
  semester: z.string(),
  totalCredits: z.string(),
  averageScore: z.string(),
  rankingClass: z.string(),
  averageCreditsOfSameGrader: z.string(),
  classRankPercentage: z.string(),
  averageScoresOfSameGrader: z.string(),
  departmentRankPercentage: z.string(),
  rankingDepartmentNumer: z.string(),
  rankingClassDenom: z.string(),
  rankingDepartmentDenom: z.string(),
  rankingClassNumer: z.string(),
  rankingDepartment: z.string(),
}).passthrough()

const totalAverageScoreSchema = z
  .object({
    averageCreditsOfSameGrader: z.string(),
    classRankPercentage: z.string(),
    averageScoresOfSameGrader: z.string(),
    departmentRankPercentage: z.string(),
    totalCredits: z.string(),
    averageScore: z.string(),
    rankingClass: z.string(),
    rankingDepartmentNumer: z.string(),
    rankingClassDenom: z.string(),
    rankingDepartmentDenom: z.string(),
    rankingClassNumer: z.string(),
    rankingDepartment: z.string(),
  })
  .passthrough()

const conductRecordItemSchema = z.object({
  score: z.union([z.number(), z.string()]),
  academicYear: z.string(),
  semester: z.string(),
})

const gradeRecordItemSchema = z.object({
  academicYearSemester: z.string(),
  requiredOrElectiveCourse: z.string(),
  score: z.string(),
  academicYear: z.string(),
  courseCode: z.string(),
  courseName: z.string(),
  semester: z.string(),
  credit: z.string(),
  remark: z.string(),
  scoreIfPass: z.string().optional(),
}).passthrough()

const exportStudentDataSchema = z.array(
  z.object({
    "課業學習": z.object({
      totalCredits: z.string(),
      coursePlan: coursePlanSchema,
      aboutMe: aboutMeSchema,
      showTcres: z.string(),
      rankingClass: z.string(),
      abroadGradeRecordList: z.array(z.unknown()),
      graduationLanguageList: z.array(z.unknown()),
      rankingClassDenom: z.string(),
      rankingDepartmentDenom: z.string(),
      waivedCourseList: z.array(z.unknown()),

      enrollmentHistoryList: z.array(enrollmentHistoryItemSchema),
      averageScoreList: z.array(averageScoreItemSchema),
      alertForEvaluationList: z.array(z.unknown()),
      totalAverageScore: totalAverageScoreSchema,
      rankingDepartment: z.string(),
      conductRecordList: z.array(conductRecordItemSchema),

      gradeRecordList: z.array(
        z.object({
          AcademicYear: z.string(),
          GradeRecords: z.array(gradeRecordItemSchema),
        }).passthrough()
      ),
      alertForCreditList: z.array(z.unknown()),
    }).passthrough(),
  }).passthrough()
).min(1)

export default function Dashboard() {
  const [studentType, setStudentType] = useState<"general" | "dual">("general")
  const [jsonData, setJsonData] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const { error, errorType, isLoading, result, clearError, clearResult, submitToApi, setError, setErrorType } = useErrorHandler()

  // 重置文件輸入（解決同檔重複上傳問題）
  const resetFileInput = useCallback(() => {
    try {
      if (inputRef.current) {
        inputRef.current.value = ""
      }
    } catch (e) {
      // 忽略錯誤
    }
  }, [])

  // 檢查是否為雙主修/輔系學生
  const checkStudentIdentity = useCallback((data: z.infer<typeof exportStudentDataSchema>): "general" | "dual" => {
    const aboutMe = data[0]["課業學習"].aboutMe
    const doubleMajor = aboutMe.doubleMajor?.trim() || ""
    const minor1 = aboutMe.minor1?.trim() || ""
    const minor2 = aboutMe.minor2?.trim() || ""
    
    // 如果有雙主修或輔系資料，則為雙輔生
    if (doubleMajor || minor1 || minor2) {
      return "dual"
    }
    return "general"
  }, [])

  const handleFile = useCallback((file: File) => {
    // 清除之前的結果和錯誤
    clearError()
    clearResult()
    setJsonData(null)
    setFileName(null)

    if (!file.name.endsWith(".json")) {
      setError("請上傳 .json 格式的檔案")
      setErrorType("format")
      resetFileInput()
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string
        const parsed = JSON.parse(text)

        const validationResult = exportStudentDataSchema.safeParse(parsed)
        if (!validationResult.success) {
          const issue = validationResult.error.issues[0]
          const path = issue?.path?.length ? issue.path.join(".") : "(root)"
          setError(`JSON 欄位格式不符合範例：${path} ${issue.message}`)
          setErrorType("format")
          resetFileInput()
          return
        }

        // 檢查 JSON 中的身分與選擇的身分是否一致
        const detectedIdentity = checkStudentIdentity(validationResult.data)
        
        if (detectedIdentity === "dual" && studentType === "general") {
          setError("偵測到 JSON 中包含雙主修/輔系資料，請切換至「雙輔生」身分後重新上傳")
          setErrorType("format")
          resetFileInput()
          return
        }
        
        if (detectedIdentity === "general" && studentType === "dual") {
          setError("偵測到 JSON 中無雙主修/輔系資料，請切換至「一般生」身分後重新上傳")
          setErrorType("format")
          resetFileInput()
          return
        }

        setJsonData(JSON.stringify(parsed, null, 2))
        setFileName(file.name)
        submitToApi(parsed, studentType)
        // 上傳成功後也要重置，這樣使用者可以再次選擇相同的檔案
        resetFileInput()
        
      } catch {
        setError("無法解析 JSON 檔案，請確認檔案格式正確")
        setErrorType("format")
        resetFileInput()
      }
    }
    reader.readAsText(file)
  }, [clearError, clearResult, submitToApi, setError, setErrorType, studentType, checkStudentIdentity, resetFileInput])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }, [handleFile])

  const clearFile = useCallback(() => {
    setJsonData(null)
    setFileName(null)
    clearError()
    clearResult()
    resetFileInput()
  }, [clearError, clearResult, resetFileInput])

  return (
    <div className="min-h-screen bg-background p-6 md:p-10">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">
            畢業審判官
          </h1>
          <p className="text-muted-foreground">
            上傳學生資料 JSON 檔案進行畢業審查
          </p>
        </div>

        {/* Tabs */}
        <Tabs 
          value={studentType} 
          onValueChange={(v) => {
            setStudentType(v as "general" | "dual")
            // 切換身分時清除之前的錯誤和結果，讓用戶重新上傳
            clearError()
            clearResult()
            setJsonData(null)
            setFileName(null)
            resetFileInput()
          }} 
          className="w-full"
        >
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
            <TabsTrigger value="general" className="text-base">
              一般生
            </TabsTrigger>
            <TabsTrigger value="dual" className="text-base">
              雙輔生
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Upload Zone */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileJson className="h-5 w-5 text-primary" />
              上傳 JSON 檔案
              {studentType === "general" ? " (一般生)" : " (雙輔生)"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`
                relative border-2 border-dashed rounded-lg p-12 text-center
                transition-all duration-200 cursor-pointer
                ${isDragging 
                  ? "border-primary bg-primary/5" 
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
                }
                ${error ? "border-destructive" : ""}
              `}
            >
              <input
                type="file"
                accept=".json"
                ref={inputRef}
                onChange={handleInputChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="space-y-4">
                <div className={`
                  mx-auto w-16 h-16 rounded-full flex items-center justify-center
                  ${isDragging ? "bg-primary/10" : "bg-muted"}
                `}>
                  <Upload className={`h-8 w-8 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
                </div>
                <div>
                  <p className="text-foreground font-medium">
                    拖放檔案至此處，或點擊選擇檔案
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    支援 .json 格式
                  </p>
                </div>
              </div>
            </div>

            {/* 錯誤訊息 */}
            <ErrorMessage message={error} type={errorType} onClose={clearError} />

            {/* 載入中 */}
            {isLoading && (
              <div className="flex items-center justify-center gap-2 text-muted-foreground text-sm mt-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>分析中，請稍候...</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 畢業審查結果 */}
        {result && !isLoading && (
          <GraduationResult result={result} />
        )}

        {/* JSON Preview */}
        {jsonData && (
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileJson className="h-5 w-5 text-primary" />
                  {fileName}
                </CardTitle>
                <button
                  onClick={clearFile}
                  className="p-2 rounded-md hover:bg-muted transition-colors"
                  aria-label="清除檔案"
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="bg-muted rounded-lg p-4 max-h-96 overflow-auto">
                <pre className="text-sm font-mono text-foreground whitespace-pre-wrap break-all">
                  {jsonData}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
