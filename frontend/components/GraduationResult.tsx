"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, XCircle, BookOpen, Dumbbell, FileText } from "lucide-react"
import { type GraduationResult as GraduationResultType } from "@/hooks/useErrorHandler"

interface GraduationResultProps {
  result: GraduationResultType
}

export default function GraduationResult({ result }: GraduationResultProps) {
  const { summary, is_eligible_to_graduate } = result

  // 計算各項缺少的學分
  const missingRequired = Math.max(0, summary.required_credits_needed - summary.required_credits_earned)
  const missingGeneral = Math.max(0, summary.general_credits_needed - summary.general_credits_earned)
  const missingElective = Math.max(0, summary.elective_credits_needed - summary.elective_credits_earned)
  const missingPE = Math.max(0, summary.pe_credits_needed - summary.pe_credits_earned)

  return (
    <div className="space-y-6">
      {/* 畢業可否大標題 */}
      <Card className={is_eligible_to_graduate ? "border-green-500 bg-green-50" : "border-red-500 bg-red-50"}>
        <CardContent className="py-8">
          <div className="flex flex-col items-center gap-4">
            {is_eligible_to_graduate ? (
              <>
                <CheckCircle2 className="h-16 w-16 text-green-600" />
                <h2 className="text-3xl font-bold text-green-700">恭喜！符合畢業資格</h2>
                <p className="text-green-600">
                  {result.dept_name} - {result.applicable_year}學年度
                </p>
              </>
            ) : (
              <>
                <XCircle className="h-16 w-16 text-red-600" />
                <h2 className="text-3xl font-bold text-red-700">尚未符合畢業資格</h2>
                <p className="text-red-600">
                  {result.dept_name} - {result.applicable_year}學年度
                </p>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 學分統計概覽 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">學分統計概覽</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* 必修 */}
            <div className={`text-center p-3 rounded-lg border ${missingRequired === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <p className="text-xs text-muted-foreground mb-1">必修</p>
              <p className={`text-2xl font-bold ${missingRequired === 0 ? "text-green-700" : "text-red-700"}`}>{summary.required_credits_earned}</p>
              <p className="text-xs text-muted-foreground">/ {summary.required_credits_needed}</p>
            </div>
            {/* 選修 */}
            <div className={`text-center p-3 rounded-lg border ${missingElective === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <p className="text-xs text-muted-foreground mb-1">選修</p>
              <p className={`text-2xl font-bold ${missingElective === 0 ? "text-green-700" : "text-red-700"}`}>{summary.elective_credits_earned}</p>
              <p className="text-xs text-muted-foreground">/ {summary.elective_credits_needed}</p>
            </div>
            {/* 通識 */}
            <div className={`text-center p-3 rounded-lg border ${missingGeneral === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <p className="text-xs text-muted-foreground mb-1">通識</p>
              <p className={`text-2xl font-bold ${missingGeneral === 0 ? "text-green-700" : "text-red-700"}`}>{summary.general_credits_earned}</p>
              <p className="text-xs text-muted-foreground">/ {summary.general_credits_needed}</p>
            </div>
            {/* 體育 */}
            <div className={`text-center p-3 rounded-lg border ${missingPE === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <p className="text-xs text-muted-foreground mb-1">體育</p>
              <p className={`text-2xl font-bold ${missingPE === 0 ? "text-green-700" : "text-red-700"}`}>{summary.pe_credits_earned}</p>
              <p className="text-xs text-muted-foreground">/ {summary.pe_credits_needed}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 必修課程 & 選修學分 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 必修課程 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              必修課程
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`p-4 rounded-lg border ${missingRequired === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">已修學分</span>
                  <span className="text-2xl font-bold">{summary.required_credits_earned}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">需修學分</span>
                  <span className="text-lg">{summary.required_credits_needed}</span>
                </div>
                {missingRequired > 0 ? (
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-red-600 font-medium">缺少學分</span>
                    <span className="text-red-600 font-bold">{missingRequired}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2 pt-2 border-t text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">已完成</span>
                  </div>
                )}
              </div>
            </div>

            {/* 必修課程列表 */}
            {result.required_courses && (
              <div className="mt-6 space-y-4">
                {result.required_courses.passed.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-green-700 mb-2">✓ 已通過 ({result.required_courses.passed.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {result.required_courses.passed.map((course, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
                        >
                          {course}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {result.required_courses.missing.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-red-700 mb-2">✗ 缺少 ({result.required_courses.missing.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {result.required_courses.missing.map((course, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm"
                        >
                          {course}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 選修學分 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              選修學分
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`p-4 rounded-lg border ${missingElective === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">已修學分</span>
                  <span className="text-2xl font-bold">{summary.elective_credits_earned}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">需修學分</span>
                  <span className="text-lg">{summary.elective_credits_needed}</span>
                </div>
                {missingElective > 0 ? (
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-red-600 font-medium">缺少學分</span>
                    <span className="text-red-600 font-bold">{missingElective}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2 pt-2 border-t text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">已完成</span>
                  </div>
                )}
              </div>
            </div>
            
            {/* 系內/系外選修細分（如果有資料） */}
            {result.elective && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="text-center p-3 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">系內選修</p>
                  <p className="text-xl font-bold text-primary">{result.elective.in_dept_credits}</p>
                  <p className="text-xs text-muted-foreground">學分</p>
                </div>
                <div className="text-center p-3 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">系外選修</p>
                  <p className="text-xl font-bold text-primary">{result.elective.out_dept_credits}</p>
                  <p className="text-xs text-muted-foreground">學分</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 通識課程 & 體育學分 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 通識課程 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              通識課程
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`p-4 rounded-lg border ${missingGeneral === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">已修學分</span>
                  <span className="text-2xl font-bold">{summary.general_credits_earned}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">需修學分</span>
                  <span className="text-lg">{summary.general_credits_needed}</span>
                </div>
                {missingGeneral > 0 ? (
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-red-600 font-medium">缺少學分</span>
                    <span className="text-red-600 font-bold">{missingGeneral}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2 pt-2 border-t text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">已完成</span>
                  </div>
                )}
              </div>
            </div>

            {/* 通識領域分布（如果有資料） */}
            {result.general_education && result.general_education.by_category && (
              <div className="mt-6">
                <p className="text-sm font-semibold mb-3">各領域學分分布</p>
                <div className="grid grid-cols-3 gap-3">
                  {Object.entries(result.general_education.by_category).map(([category, credits]) => (
                    <div key={category} className="text-center p-3 bg-muted rounded-lg border">
                      <p className="text-xs text-muted-foreground mb-1">{category}</p>
                      <p className="text-xl font-bold text-primary">{credits}</p>
                      <p className="text-xs text-muted-foreground">學分</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 體育學分 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Dumbbell className="h-5 w-5" />
              體育學分
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`p-4 rounded-lg border ${missingPE === 0 ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">已修學分</span>
                  <span className="text-2xl font-bold">{summary.pe_credits_earned}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">需修學分</span>
                  <span className="text-lg">{summary.pe_credits_needed}</span>
                </div>
                {missingPE > 0 ? (
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-red-600 font-medium">缺少學分</span>
                    <span className="text-red-600 font-bold">{missingPE}</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2 pt-2 border-t text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">已完成</span>
                  </div>
                )}
              </div>
            </div>

            {/* 體育課程列表（如果有資料） */}
            {result.physical_education && result.physical_education.courses.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-muted-foreground mb-2">已修課程</p>
                <div className="flex flex-wrap gap-2">
                  {result.physical_education.courses.map((course, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                    >
                      {course}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
