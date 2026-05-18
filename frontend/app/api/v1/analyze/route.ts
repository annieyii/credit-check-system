import { NextRequest, NextResponse } from 'next/server'

// Mock API for testing - 模擬後端回傳
export async function POST(request: NextRequest) {
  // 模擬網路延遲
  await new Promise(resolve => setTimeout(resolve, 1000))

  // 模擬後端回傳的資料
  const mockResponse = {
    dept_name: "資訊科學系",
    applicable_year: "114",
    summary: {
      total_credits_earned: 92,
      required_credits_earned: 60,
      required_credits_needed: 72,
      pe_credits_earned: 2,
      pe_credits_needed: 4,
      general_credits_earned: 6,
      general_credits_needed: 8,
      elective_credits_earned: 20,
      elective_credits_needed: 18
    },
    // 必修課程回傳
    required_courses: {
      passed: ["計算機概論", "資料結構"],
      missing: ["作業系統", "編譯器"]
    },
    // 輔系詳細資料
    minor: {
      passed: ["日語初級（一）", "日語初級（二）"],
      missing: ["日本文學概論", "日語會話"],
      credits_earned: 20,
      credits_needed: 50
    },
    // 通識詳細資料 (來自 analyze_general_education)
    general_education: {
      credits_earned: 6,
      credits_needed: 8,
      passed: false,
      by_category: {
        "人文": 3,
        "社會": 3,
        "自然": 0
      }
    },
    // 體育詳細資料 (來自 analyze_pe)
    physical_education: {
      credits_earned: 2,
      credits_needed: 4,
      passed: false,
      courses: ["體育（一）", "體育（二）"]
    },
    // 選修詳細資料 (來自 analyze_elective)
    elective: {
      credits_earned: 20,
      credits_needed: 18,
      passed: true,
      in_dept_credits: 15,
      out_dept_credits: 5
    },
    is_eligible_to_graduate: false
  }

  return NextResponse.json(mockResponse)
}