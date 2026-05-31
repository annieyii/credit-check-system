"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, XCircle, BookOpen, Dumbbell, FileText, GraduationCap } from "lucide-react"
import { type GraduationResult as GraduationResultType } from "@/hooks/useErrorHandler"

interface GraduationResultProps {
  result: GraduationResultType
}

function ProgressBar({ earned, needed, color = "green" }: { earned: number; needed: number; color?: "green" | "red" | "blue" }) {
  const pct = needed > 0 ? Math.min(100, Math.round((earned / needed) * 100)) : 100
  const trackColor = "bg-gray-200"
  const fillColor = color === "green" ? "bg-green-500" : color === "red" ? "bg-red-500" : "bg-blue-500"
  return (
    <div className={`w-full h-1.5 rounded-full ${trackColor} mt-2`}>
      <div className={`h-1.5 rounded-full ${fillColor} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function CreditBlock({
  earned, needed, accentColor = "green"
}: {
  earned: number
  needed: number
  accentColor?: "green" | "red"
}) {
  const done = earned >= needed
  const missing = Math.max(0, needed - earned)
  const bg = done ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
  return (
    <div className={`p-4 rounded-xl border ${bg}`}>
      <div className="mb-1">
        <span className="text-muted-foreground text-sm">已修 / 需修</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold">{earned}</span>
        <span className="text-muted-foreground text-base">/ {needed}</span>
      </div>
      <ProgressBar earned={earned} needed={needed} color={done ? "green" : "red"} />
      <div className="mt-2">
        {done ? (
          <span className="inline-flex items-center gap-1 text-green-600 text-xs font-medium">
            <CheckCircle2 className="h-3.5 w-3.5" /> 已完成
          </span>
        ) : (
          <span className="text-red-600 text-xs font-medium">缺少 {missing} 學分</span>
        )}
      </div>
    </div>
  )
}

export default function GraduationResult({ result }: GraduationResultProps) {
  const { summary, is_eligible_to_graduate } = result

  const missingRequired = Math.max(0, summary.required_credits_needed - summary.required_credits_earned)
  const missingGeneral = Math.max(0, summary.general_credits_needed - summary.general_credits_earned)
  const missingElective = Math.max(0, summary.elective_credits_needed - summary.elective_credits_earned)
  const missingPE = Math.max(0, summary.pe_credits_needed - summary.pe_credits_earned)

  const statItems = [
    { label: "必修", earned: summary.required_credits_earned, needed: summary.required_credits_needed },
    { label: "選修", earned: summary.elective_credits_earned, needed: summary.elective_credits_needed },
    { label: "通識", earned: summary.general_credits_earned, needed: summary.general_credits_needed },
    { label: "體育", earned: summary.pe_credits_earned, needed: summary.pe_credits_needed },
  ]

  return (
    <div className="space-y-6">
      {/* 畢業可否大標題 */}
      <Card className={`shadow-md border-2 overflow-hidden ${is_eligible_to_graduate ? "border-green-400" : "border-red-400"}`}>
        <div className={`py-10 px-6 ${is_eligible_to_graduate ? "bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50" : "bg-gradient-to-br from-red-50 via-rose-50 to-pink-50"}`}>
          <div className="flex flex-col items-center gap-4">
            <div className={`p-4 rounded-full ${is_eligible_to_graduate ? "bg-green-100" : "bg-red-100"}`}>
              {is_eligible_to_graduate
                ? <GraduationCap className="h-14 w-14 text-green-600" />
                : <XCircle className="h-14 w-14 text-red-600" />
              }
            </div>
            <div className="text-center">
              <h2 className={`text-3xl font-bold ${is_eligible_to_graduate ? "text-green-700" : "text-red-700"}`}>
                {is_eligible_to_graduate ? "恭喜！符合畢業資格" : "尚未符合畢業資格"}
              </h2>
              <p className={`mt-1 text-sm ${is_eligible_to_graduate ? "text-green-600" : "text-red-500"}`}>
                {result.dept_name}　{result.applicable_year} 學年度
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* 學分統計概覽 */}
      <Card className="shadow-sm">
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-base font-semibold tracking-wide text-muted-foreground uppercase">學分統計概覽</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {statItems.map(({ label, earned, needed }) => {
              const done = earned >= needed
              const pct = needed > 0 ? Math.min(100, Math.round((earned / needed) * 100)) : 100
              return (
                <div key={label} className={`p-4 rounded-xl border text-center ${done ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                  <p className="text-xs text-muted-foreground mb-1">{label}</p>
                  <p className={`text-2xl font-bold ${done ? "text-green-700" : "text-red-700"}`}>{earned}</p>
                  <p className="text-xs text-muted-foreground">/ {needed} 學分</p>
                  <ProgressBar earned={earned} needed={needed} color={done ? "green" : "red"} />
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* 必修課程 & 選修學分 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 必修課程 */}
        <Card className="shadow-sm">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-blue-100"><FileText className="h-4 w-4 text-blue-600" /></span>
              必修課程
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <CreditBlock earned={summary.required_credits_earned} needed={summary.required_credits_needed} />

            {result.required_courses && (() => {
              const main = result.required_courses.main_major
              const dm = result.required_courses.double_major
              const renderBlock = (
                title: string,
                block: NonNullable<typeof main>,
                badgeColor: string,
              ) => {
                const missing = Math.max(0, block.credits_needed - block.credits_earned)
                return (
                  <div className="border rounded-xl p-4 bg-background">
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor}`}>{title}</span>
                      <span className="font-semibold text-sm">{block.dept_name}</span>
                      <span className="text-xs text-muted-foreground ml-auto">({block.year} 學年度)</span>
                    </div>
                    <CreditBlock earned={block.credits_earned} needed={block.credits_needed} />
                    <div className="mt-4 space-y-3">
                      {block.passed.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-green-700 mb-1.5">已通過 ({block.passed.length})</p>
                          <div className="flex flex-wrap gap-1.5">
                            {block.passed.map((c, i) => (
                              <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {block.missing.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-red-700 mb-1.5">缺少 ({block.missing.length})</p>
                          <div className="flex flex-wrap gap-1.5">
                            {block.missing.map((c, i) => (
                              <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 rounded-full text-xs font-medium">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              }

              if (main) {
                return (
                  <div className="mt-4 space-y-3">
                    {renderBlock("主修", main, "bg-blue-100 text-blue-800")}
                    {dm && renderBlock("雙主修", dm, "bg-purple-100 text-purple-800")}
                  </div>
                )
              }

              return (
                <div className="mt-4 space-y-4">
                  {result.required_courses.passed.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-green-700 mb-2">已通過 ({result.required_courses.passed.length})</p>
                      <div className="flex flex-wrap gap-2">
                        {result.required_courses.passed.map((course, index) => (
                          <span key={index} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">{course}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {result.required_courses.missing.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-red-700 mb-2">缺少 ({result.required_courses.missing.length})</p>
                      <div className="flex flex-wrap gap-2">
                        {result.required_courses.missing.map((course, index) => (
                          <span key={index} className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">{course}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
          </CardContent>
        </Card>

        {/* 選修學分 */}
        <Card className="shadow-sm">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-violet-100"><BookOpen className="h-4 w-4 text-violet-600" /></span>
              選修學分
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <CreditBlock earned={summary.elective_credits_earned} needed={summary.elective_credits_needed} />

            {result.elective && (
              <div className="grid grid-cols-2 gap-3 mt-4">
                {[
                  { label: "系內選修", credits: result.elective.in_dept_credits, courses: result.elective.in_dept_courses },
                  { label: "系外選修", credits: result.elective.out_dept_credits, courses: result.elective.out_dept_courses },
                ].map(({ label, credits, courses }) => (
                  <div key={label} className="p-3 bg-muted rounded-xl border">
                    <p className="text-xs text-muted-foreground text-center">{label}</p>
                    <p className="text-2xl font-bold text-primary text-center mt-1">{credits}</p>
                    <p className="text-xs text-muted-foreground text-center mb-2">學分</p>
                    {courses && courses.length > 0 ? (
                      <ul className="space-y-1 text-xs max-h-48 overflow-y-auto">
                        {courses.map((c, i) => (
                          <li key={`${c.courseCode}-${i}`} className="flex justify-between gap-2 border-b border-muted-foreground/10 pb-1">
                            <span className="truncate">{c.courseName}</span>
                            <span className="text-muted-foreground shrink-0">{c.credits} 學分</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground text-center">尚無課程</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 通識課程 & 體育學分 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 通識課程 */}
        <Card className="shadow-sm">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-amber-100"><BookOpen className="h-4 w-4 text-amber-600" /></span>
              通識課程
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <CreditBlock earned={summary.general_credits_earned} needed={summary.general_credits_needed} />

            {result.general_education?.violations && result.general_education.violations.length > 0 && (
              <div className="mt-4 p-3 rounded-xl border border-red-300 bg-red-50 text-sm text-red-900">
                <p className="font-semibold mb-1">⚠️ 未符合的規則</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {result.general_education.violations.map((v, i) => <li key={i}>{v}</li>)}
                </ul>
              </div>
            )}

            {result.general_education?.info_warning_courses && result.general_education.info_warning_courses.length > 0 && (
              <div className="mt-4 p-3 rounded-xl border border-amber-300 bg-amber-50 text-sm text-amber-900">
                <p className="font-semibold mb-1">⚠️ 誤修資訊通識（不採計）</p>
                <p className="mb-2 text-xs">資科系免修資訊通識，下列課程之學分與成績皆不採計：</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {result.general_education.info_warning_courses.map((c, i) => (
                    <li key={i}>{c.courseName}（{c.credits} 學分）</li>
                  ))}
                </ul>
              </div>
            )}

            {result.general_education?.by_category && (
              <div className="mt-5">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">各領域學分分布（已採計）</p>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(result.general_education.by_category).map(([category, credits]) => {
                    const limits = result.general_education?.limits?.[category]
                    const raw = result.general_education?.raw_by_category?.[category]
                    const rangeLabel = limits ? (limits[0] === limits[1] ? `${limits[0]}` : `${limits[0]}-${limits[1]}`) : ""
                    return (
                      <div key={category} className="text-center p-3 bg-muted rounded-xl border">
                        <p className="text-xs text-muted-foreground mb-1">{category}</p>
                        <p className="text-xl font-bold text-primary">{credits}</p>
                        <p className="text-xs text-muted-foreground">{rangeLabel ? `(${rangeLabel})` : "學分"}</p>
                        {typeof raw === "number" && raw > Number(credits) && (
                          <p className="text-[10px] text-amber-700 mt-1">超修 {raw - Number(credits)}</p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {result.general_education && typeof result.general_education.core_count === "number" && (
              <div className="mt-4 p-3 bg-muted rounded-xl border">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold">核心通識</span>
                  <span className={`text-sm font-bold ${(result.general_education.core_count ?? 0) >= (result.general_education.core_required ?? 2) ? "text-green-700" : "text-red-700"}`}>
                    {result.general_education.core_count} / {result.general_education.core_required} 個不同領域
                  </span>
                </div>
                {result.general_education.core_domains_taken && result.general_education.core_domains_taken.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">已修領域：{result.general_education.core_domains_taken.join("、")}</p>
                )}
                {result.general_education.core_courses && result.general_education.core_courses.length > 0 && (
                  <ul className="mt-3 space-y-1 text-xs">
                    {result.general_education.core_courses.map((c, i) => (
                      <li key={`${c.courseCode}-${i}`} className="flex justify-between items-center gap-2 px-2 py-1 bg-background rounded-lg border">
                        <span className="flex items-center gap-2 min-w-0">
                          <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-800 shrink-0">{c.category}</span>
                          <span className="truncate">{c.courseName}</span>
                          {c.source === "waived" && <span className="text-amber-700 shrink-0">（抵免）</span>}
                        </span>
                        <span className="text-muted-foreground shrink-0">{c.credits} 學分</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {result.general_education?.taken_courses && result.general_education.taken_courses.length > 0 && (
              <div className="mt-5">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">已修通識課程</p>
                <ul className="space-y-1 text-sm max-h-64 overflow-y-auto pr-1">
                  {result.general_education.taken_courses.map((c, i) => (
                    <li key={`${c.courseCode}-${i}`} className="flex justify-between items-center gap-2 px-3 py-2 bg-muted rounded-lg border">
                      <span className="flex items-center gap-2 min-w-0">
                        <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800 shrink-0">{c.category}</span>
                        <span className="truncate">{c.courseName}</span>
                        {c.source === "waived" && <span className="text-xs text-amber-700 shrink-0">（抵免）</span>}
                      </span>
                      <span className="text-muted-foreground text-xs shrink-0">{c.credits} 學分</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 體育學分 */}
        <Card className="shadow-sm">
          <CardHeader className="pb-3 border-b">
            <CardTitle className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-100"><Dumbbell className="h-4 w-4 text-emerald-600" /></span>
              體育學分
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <CreditBlock earned={summary.pe_credits_earned} needed={summary.pe_credits_needed} />

            {result.physical_education?.senior_warning && (
              <div className="mt-4 p-3 rounded-xl border border-amber-300 bg-amber-50 text-sm text-amber-900">
                <p className="font-semibold mb-1">⚠️ 大四加修體育確認</p>
                <p>
                  偵測到大四學期
                  {` ${result.physical_education.senior_warning_semesters?.join("、")} `}
                  修了 2 門必修體育課。請確認是否已申請大四加修體育課，否則僅以 1 門計入。
                </p>
              </div>
            )}

            {result.physical_education?.course_details && result.physical_education.course_details.length > 0 ? (
              <div className="mt-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">已修課程</p>
                <ul className="space-y-1 text-sm max-h-64 overflow-y-auto pr-1">
                  {result.physical_education.course_details.map((c, i) => {
                    const statusColor = c.status === "通過" ? "bg-green-100 text-green-800" : c.status === "重複不計" ? "bg-red-100 text-red-800" : "bg-orange-100 text-orange-800"
                    return (
                      <li key={`${c.courseCode}-${i}`} className="flex justify-between items-center gap-2 px-3 py-2 bg-muted rounded-lg border">
                        <span className="flex items-center gap-2 min-w-0">
                          <span className={`px-2 py-0.5 text-xs rounded-full shrink-0 ${statusColor}`}>{c.status}</span>
                          <span className="truncate">{c.courseName}</span>
                        </span>
                        <span className="text-muted-foreground text-xs shrink-0">
                          {c.semester && c.semester !== "waived" ? c.semester : "抵免"}
                        </span>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ) : (
              result.physical_education && result.physical_education.courses.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">已修課程</p>
                  <div className="flex flex-wrap gap-2">
                    {result.physical_education.courses.map((course, index) => (
                      <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">{course}</span>
                    ))}
                  </div>
                </div>
              )
            )}
          </CardContent>
        </Card>
      </div>

      {/* 輔系學分 */}
      {(result.minor_details && result.minor_details.length > 0
        ? result.minor_details
        : result.minor
          ? [{ dept_name: "", applicable_year: "", result: result.minor }]
          : []
      ).map((item, idx) => {
        const minor = item.result
        if (!minor) return null
        const label = item.dept_name
          ? `輔系${result.minor_details && result.minor_details.length > 1 ? `${idx + 1}` : ""}：${item.dept_name}`
          : "輔系學分"
        return (
          <Card key={idx} className="shadow-sm">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-teal-100"><BookOpen className="h-4 w-4 text-teal-600" /></span>
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <CreditBlock earned={minor.credits_earned} needed={minor.credits_needed} />
              <div className="mt-5 space-y-4">
                {minor.passed.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">已通過 ({minor.passed.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {minor.passed.map((course, index) => (
                        <span key={index} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">{course}</span>
                      ))}
                    </div>
                  </div>
                )}
                {minor.missing.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">缺少 ({minor.missing.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {minor.missing.map((course, index) => (
                        <span key={index} className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">{course}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
