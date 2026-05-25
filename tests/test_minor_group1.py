import json

from backend.database import get_db
from backend.minor import analyze_minor as analyze_minor_group1, _detect_minor_info, _parse_minor_courses


def analyze_student_minor_info(file_path: str):
    """分析學生的輔系資訊"""
    print(f"📋 分析檔案：{file_path}")
    print("="*60)

    try:
        with open(file_path, encoding="utf-8") as f:
            session_data = json.load(f)

        # 取得學生基本資訊
        about = session_data[0]["課業學習"]["aboutMe"]
        student_name = about.get("chineseName", "未知")
        student_number = about.get("studentNumber", "")
        register_major = about.get("registerMajor", "")
        register_minor = about.get("registerMinor", "")
        minor1 = about.get("minor1", "")

        print("👤 學生資訊：")
        print(f"  姓名：{student_name}")
        print(f"  學號：{student_number}")
        print(f"  主修：{register_major}")
        print(f"  輔系：{register_minor}")
        print(f"  輔系年度：{minor1}")

        # 自動偵測輔系
        detected_minor = _detect_minor_info(session_data)
        if detected_minor:
            minor_dept, minor_year = detected_minor
            print(f"  🤖 自動偵測輔系：{minor_dept}（{minor_year}）")

            # 分析輔系課程
            minor_courses = _parse_minor_courses(session_data, minor_dept)
            print(f"  📚 輔系相關課程：{len(minor_courses)} 門")
            for course, credit in sorted(minor_courses.items()):
                print(f"    ✓ {course}（{credit} 學分）")

            # 執行輔系分析
            try:
                result = analyze_minor_group1(session_data, minor_dept, minor_year)
                print(f"\n📊 {minor_dept} 輔系畢業分析：")
                print(f"  已修課程：{len(result['passed'])} 門")
                for course in result['passed']:
                    credit = minor_courses.get(course, 0)
                    print(f"    ✓ {course}（{credit} 學分）")

                print(f"  未修課程：{len(result['missing'])} 門")
                for course in result['missing']:
                    print(f"    ✗ {course}")

                print(f"  學分進度：{result['credits_earned']} / {result['credits_needed']}")

                # 判斷是否符合畢業標準
                if result['credits_earned'] >= result['credits_needed']:
                    print("  🎉 畢業狀態：✅ 符合輔系畢業要求")
                else:
                    deficit = result['credits_needed'] - result['credits_earned']
                    print(f"  ❌ 畢業狀態：學分不足（差 {deficit} 學分）")

                return result

            except Exception as e:
                print(f"  ❌ 金融系分析失敗：{e}")
                return None
        else:
            print("  🤖 未偵測到輔系資訊")
            return None

    except FileNotFoundError:
        print(f"❌ 找不到檔案：{file_path}")
        return None
    except Exception as e:
        print(f"❌ 分析失敗：{e}")
        return None


def run_all_group1_minors(student_file: str):
    """測試所有 Group 1 系所的輔系分析"""
    print("\n🎯 測試所有 Group 1 輔系")
    print("="*60)

    # Group 1 系所列表
    group1_minors = [
        "風險管理與保險學系",
        "韓國語文學系",
        "阿拉伯語文學系",
        "金融系",
        "越南語文學系",
        "資訊系",
        "資管系",
        "財管系",
        "財政系財政管理組",
        "財政系稅務組",
        "財政系公共經濟組",
        "西班牙語文學系"
    ]

    try:
        with open(student_file, encoding="utf-8") as f:
            session_data = json.load(f)

        about = session_data[0]["課業學習"]["aboutMe"]
        student_number = about.get("studentNumber", "")
        year = student_number[:3] if student_number else "111"

        print(f"👤 學生：{about.get('chineseName', '未知')}")
        print(f"📚 測試各輔系畢業要求（{year} 年度）：\n")

        results = {}
        for minor in group1_minors:
            try:
                result = analyze_minor_group1(session_data, minor, year)
                status = "✅ 符合" if result['credits_earned'] >= result['credits_needed'] else f"❌ 差 {result['credits_needed'] - result['credits_earned']} 學分"
                print(f"  {minor}: {status} ({result['credits_earned']}/{result['credits_needed']})")
                results[minor] = result
            except Exception as e:
                print(f"  {minor}: ❌ 分析失敗 ({e})")

        return results

    except Exception as e:
        print(f"❌ 測試失敗：{e}")
        return {}


def test_finance_minor():
    """測試金融系輔系（使用真實JSON檔案）"""
    print("\n=== 測試金融系輔系 ===")

    test_file = "tests/test_data/cs_minor_finance.json"

    try:
        import json
        with open(test_file, encoding="utf-8") as f:
            session_data = json.load(f)

        # 確保 session_data 是列表形式
        if isinstance(session_data, dict):
            session_data = [session_data]

        about = session_data[0]["課業學習"]["aboutMe"]
        student_name = about.get("studentName", "未知")
        student_number = about.get("studentNumber", "")
        register_minor = about.get("registerMinor", "")

        print(f"  學生：{student_name}")
        print(f"  學號：{student_number}")
        print(f"  主修：{about.get('registerMajor', '')}")
        print(f"  輔系：{register_minor}")

        conn = get_db()
        try:
            result = analyze_minor_group1(
                session_data,
                "金融系",
                "112",
                conn
            )

            print("\n  📊 金融系輔系分析結果：")

            # 顯示詳細報告
            if 'detailed_report' in result:
                report = result['detailed_report']

                # 必修課程分析
                required = report['required']
                print("    📚 必修課程：")
                print(f"      已修完成：{len(required['passed'])} 門，{required['credits_earned']} 學分")
                for course in required['passed']:
                    name = course['name']
                    credits = course['credits']
                    earned = course.get('earned_credits', credits)
                    alt_info = f" (透過 {course['via_alternative']})" if 'via_alternative' in course else ""
                    print(f"        ✓ {name}（需 {credits} 學分，已修 {earned} 學分）{alt_info}")

                missing_total = 0
                for course in required['missing']:
                    missing_total += course.get('deficit', course['credits'])

                print(f"      未完成：{len(required['missing'])} 門，差 {missing_total} 學分")
                for course in required['missing']:
                    name = course['name']
                    credits = course['credits']
                    earned = course.get('earned_credits', 0)
                    deficit = course.get('deficit', credits)
                    partial = course.get('partial', False)

                    if partial:
                        alt_info = f" (透過 {course['via_alternative']})" if 'via_alternative' in course else ""
                        print(f"        ⚠️  {name}（需 {credits} 學分，已修 {earned} 學分，差 {deficit} 學分）{alt_info}")
                    else:
                        print(f"        ✗ {name}（需 {credits} 學分，未修）")

                # 群修課程分析
                group_electives = report['group_electives']
                print("    📖 群修課程：")
                print(f"      已修：{len(group_electives['passed'])} 門，{group_electives['credits_earned']} 學分")
                print(f"      應修：{group_electives['credits_needed']} 學分")

                for group_detail in group_electives['group_details']:
                    group_name = group_detail['group_name']
                    min_credits = group_detail['min_credits']
                    earned = group_detail['credits_earned']

                    print(f"        📁 {group_name}（需 {min_credits} 學分，已修 {earned} 學分）：")

                    if group_detail['passed_courses']:
                        for course in group_detail['passed_courses']:
                            print(f"          ✓ {course['name']}（{course['credits']} 學分）")

                    if group_detail['missing_courses']:
                        for course in group_detail['missing_courses']:
                            print(f"          ✗ {course['name']}（{course['credits']} 學分）")

                    # 判斷該群組是否滿足要求
                    if earned >= min_credits:
                        print("          ✅ 該群組已滿足要求")
                    else:
                        deficit = min_credits - earned
                        print(f"          ❌ 該群組還差 {deficit} 學分")
            else:
                # 簡化版顯示（如果沒有詳細報告）
                print(f"    已修課程：{len(result['passed'])} 門")
                for course in result['passed']:
                    print(f"      ✓ {course}")

                print(f"    未修課程：{len(result['missing'])} 門")
                for course in result['missing']:
                    print(f"      ✗ {course}")

            print("\n    📈 總計：")
            print(f"      已修學分：{result['credits_earned']}")
            print(f"      應修學分：{result['credits_needed']}")

            # 判斷畢業狀態
            if result['credits_earned'] >= result['credits_needed']:
                print("    🎉 畢業狀態：✅ 符合輔系畢業要求")
            else:
                deficit = result['credits_needed'] - result['credits_earned']
                print(f"    ❌ 畢業狀態：學分不足（差 {deficit} 學分）")

        except Exception as e:
            print(f"  ❌ 西文系分析失敗：{e}")
        finally:
            conn.close()

    except FileNotFoundError:
        print(f"  ❌ 找不到測試檔案：{test_file}")
    except Exception as e:
        print(f"  ❌ 讀取檔案失敗：{e}")


def main():
    """主程式"""
    print("🎓 輔系畢業分析工具")
    print("="*60)

    # 測試檔案
    test_file = "tests/test_data/111cs輔日抵免資料.json"

    # 1. 分析學生的輔系資訊
    analyze_student_minor_info(test_file)

    # 2. 測試所有 Group 1 輔系
    run_all_group1_minors(test_file)

    print("\n🎉 分析完成！")


if __name__ == "__main__":
    test_finance_minor()
    print("\n🎉 測試完成！")
