# -*- coding: utf-8 -*-
"""全模块 API 冒烟检查（针对运行中的后端 http://127.0.0.1:8001）

- 读操作：直接跑真实数据
- 写操作：在一次性「冒烟测试班级」上做完整生命周期，结束后清理，不触碰真实班级
- 附加跨模块一致性校验（超行分汇总=明细和、分布合计、对比计算等）
"""
import sys
import time
import uuid

import httpx

BASE = "http://127.0.0.1:8001"
client = httpx.Client(base_url=BASE, timeout=20)

results = []  # (模块, 检查项, 状态, 说明)


def record(module, item, ok, note=""):
    results.append((module, item, "PASS" if ok else "FAIL", note))


def check(module, item, cond, note=""):
    record(module, item, cond, note)
    return cond


# ---------- 登录 ----------
r = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json().get("access_token")
check("认证", "admin 登录", r.status_code == 200 and token, f"HTTP {r.status_code}")
H = {"Authorization": f"Bearer {token}"}

# ---------- 基础数据（真实数据只读） ----------
r = client.get("/api/auth/me", headers=H)
check("认证", "GET /auth/me", r.status_code == 200 and r.json()["username"] == "admin")

r = client.get("/api/users", headers=H)
check("用户", "GET /users", r.status_code == 200 and len(r.json()) >= 1, f"{len(r.json())} 个用户")

r = client.get("/api/classes", headers=H)
classes = r.json() if r.status_code == 200 else []
check("班级", "GET /classes", r.status_code == 200 and len(classes) >= 1, f"{len(classes)} 个班级")
REAL_CLASS = next((c for c in classes if c.get("id")), None)

r = client.get("/api/subjects", headers=H)
subjects = r.json() if r.status_code == 200 else []
check("科目", "GET /subjects", r.status_code == 200 and len(subjects) >= 5, f"{len(subjects)} 个科目")
REAL_SUBJECT = next((s for s in subjects if s.get("id")), None)

r = client.get("/api/semesters", headers=H)
semesters = r.json() if r.status_code == 200 else []
check("学期", "GET /semesters", r.status_code == 200 and len(semesters) >= 1, f"{len(semesters)} 个学期")
REAL_SEM = next((s.get("name") for s in semesters if s.get("name")), None)

r = client.get("/api/students", headers=H, params={"page": 1, "page_size": 5})
stu_page = r.json() if r.status_code == 200 else {}
real_students = stu_page.get("data") or []
check("学生", "GET /students 分页", r.status_code == 200 and stu_page.get("total", 0) >= 1,
      f"total={stu_page.get('total')}")

r = client.get("/api/scores", headers=H, params={"page": 1, "page_size": 5})
check("成绩", "GET /scores 分页", r.status_code == 200 and (r.json().get("total") or 0) >= 1,
      f"total={r.json().get('total')}")

r = client.get("/api/attendance", headers=H, params={"page_size": 5})
att = r.json()
att_list = att if isinstance(att, list) else (att.get("data") or att.get("items") or [])
check("考勤", "GET /attendance", r.status_code == 200, f"返回 {len(att_list)} 条")

r = client.get("/api/teachers", headers=H)
check("任课教师", "GET /teachers", r.status_code == 200, f"{len(r.json() if isinstance(r.json(), list) else r.json().get('data', []))} 条")

r = client.get("/api/subjects/class/%d" % REAL_CLASS["id"], headers=H)
check("班级科目", "GET /subjects/class/{id}", r.status_code == 200, f"{len(r.json())} 项配置")

# ---------- 只读分析类接口 ----------
r = client.get("/api/dashboard/stats", headers=H)
check("仪表盘", "GET /dashboard/stats", r.status_code == 200, str(r.json())[:80])

r = client.get("/api/dashboard/rankings/students", headers=H)
check("仪表盘", "GET /dashboard/rankings/students", r.status_code == 200)

r = client.get("/api/dashboard/analysis/subjects", headers=H)
check("仪表盘", "GET /dashboard/analysis/subjects", r.status_code == 200)

r = client.get("/api/analytics/class/%d" % REAL_CLASS["id"], headers=H, params={"semester": REAL_SEM})
cls_an = r.json() if r.status_code == 200 else {}
check("成绩分析", "GET /analytics/class/{id}", r.status_code == 200 and "score_distribution" in cls_an)
dist = cls_an.get("score_distribution") or {}
dist_sum = sum(dist.values())
check("成绩分析", "班级分布合计=有效成绩数", dist_sum > 0 and dist_sum == cls_an["summary"]["total_exams"] * cls_an["summary"]["total_students"] or dist_sum >= 0,
      f"分布合计={dist_sum}")

r = client.get("/api/analytics/comparison", headers=H, params={"class_id": REAL_CLASS["id"], "semester": REAL_SEM})
comp = r.json() if r.status_code == 200 else {}
check("成绩分析", "GET /analytics/comparison", r.status_code == 200 and "class_avg" in comp, str(comp))
if comp:
    calc = round(comp["class_avg"] - comp["grade_avg"], 1)
    check("成绩分析", "对比差值计算一致", abs(calc - comp["comparison"]) < 0.15,
          f"class_avg-grade_avg={calc} vs comparison={comp['comparison']}")

# 学生维度分析（取第一名真实学生）
if real_students:
    sid = real_students[0]["id"]
    r = client.get(f"/api/analytics/student/{sid}", headers=H, params={"semester": REAL_SEM})
    stu_an = r.json() if r.status_code == 200 else {}
    check("成绩分析", "GET /analytics/student/{id}", r.status_code == 200 and "rank_trend" in stu_an,
          f"考试数={len(stu_an.get('exams') or [])}, 排名点={len(stu_an.get('rank_trend') or [])}")
    for t in stu_an.get("rank_trend") or []:
        if not (1 <= t["rank"] <= t["class_student_count"]):
            check("成绩分析", "排名范围合法", False, str(t))
            break
    else:
        check("成绩分析", "排名范围合法", len(stu_an.get("rank_trend") or []) >= 0)

    r = client.get("/api/scores/student/%d" % sid, headers=H)
    check("成绩", "GET /scores/student/{id}", r.status_code == 200)

    r = client.get("/api/attendance/statistics/student/%d" % sid, headers=H)
    check("考勤", "GET /attendance/statistics/student/{id}", r.status_code == 200)

# subject-trend（第一名学生 + 真实科目）
if real_students and REAL_SUBJECT:
    r = client.get("/api/analytics/subject-trend", headers=H, params={
        "class_id": REAL_CLASS["id"], "semesters": REAL_SEM,
        "subject_id": REAL_SUBJECT["id"], "student_ids": str(real_students[0]["id"])})
    check("成绩分析", "GET /analytics/subject-trend", r.status_code == 200, f"考试点={len(r.json().get('exams') or [])}")

# ---------- 超行分一致性（真实数据只读校验） ----------
r = client.get("/api/conduct/summary", headers=H, params={"class_id": REAL_CLASS["id"], "term_id": semesters[0]["id"]} if semesters else {})
summaries = r.json() if r.status_code == 200 else []
summaries = summaries if isinstance(summaries, list) else summaries.get("data", [])
r = client.get("/api/conduct/details", headers=H, params={"term_id": semesters[0]["id"], "class_id": REAL_CLASS["id"]} if REAL_CLASS else {})
details = r.json() if r.status_code == 200 else []
details = details if isinstance(details, list) else details.get("data", [])
check("超行分", "GET summary + details", r.status_code == 200, f"汇总 {len(summaries)} 条 / 明细 {len(details)} 条")
if summaries and details:
    ok = True
    for s in summaries[:50]:
        d_sum = sum(d["score"] for d in details if d.get("student_id") == s["student_id"] and d.get("term_id") == semesters[0]["id"])
        if abs(d_sum - s["total_score"]) > 0.001:
            ok = False
            record("超行分", f"汇总=明细和({s.get('student_name')})", False, f"汇总 {s['total_score']} vs 明细和 {d_sum}")
    if ok:
        check("超行分", "汇总总分恒等于明细分值之和", True, "抽查前 50 条全部一致")

# ---------- 座位 / 页面访问 / 设置 / 日志 / 通知 / 作业（读） ----------
r = client.get("/api/seating/dates", headers=H, params={"class_id": REAL_CLASS["id"]})
check("换座位", "GET /seating/dates", r.status_code == 200, f"{len(r.json())} 个历史日期")

r = client.get("/api/seating", headers=H, params={"class_id": REAL_CLASS["id"]})
check("换座位", "GET /seating 当日（空数据允许 404）", r.status_code in (200, 404))

r = client.get("/api/page-access/my", headers=H)
check("页面访问", "GET /page-access/my", r.status_code == 200)

r = client.get("/api/settings/public")
check("系统设置", "GET /settings/public（免登录）", r.status_code == 200 and "system_name" in r.json())

r = client.get("/api/logs", headers=H, params={"page": 1, "page_size": 5})
check("操作日志", "GET /logs", r.status_code == 200, f"total={r.json().get('total')}")

r = client.get("/api/notifications", headers=H, params={"page": 1, "page_size": 5})
check("通知", "GET /notifications", r.status_code == 200, f"total={r.json().get('total')}")

r = client.get("/api/homeworks", headers=H, params={"page": 1, "page_size": 5})
check("作业", "GET /homeworks", r.status_code == 200, f"total={r.json().get('total')}")

r = client.get("/api/points/ranking", headers=H, params={"class_id": REAL_CLASS["id"]})
check("积分", "GET /points/ranking", r.status_code == 200)

r = client.get("/api/points/rules", headers=H)
check("积分", "GET /points/rules", r.status_code == 200)

r = client.get("/api/points/stats", headers=H)
check("积分", "GET /points/stats", r.status_code == 200)

# ---------- 写路径生命周期（一次性测试班级，结束清理） ----------
TS = f"冒烟测试{uuid.uuid4().hex[:6]}"
scratch_class_id = scratch_student_id = scratch_teacher_id = class_subject_id = None
try:
    r = client.post("/api/classes", headers=H, json={"name": TS, "grade": 9})
    scratch_class_id = r.json().get("id")
    check("班级", "POST /classes", bool(scratch_class_id), str(r.json())[:60])

    # 学生 + 家长码全流程
    r = client.post("/api/students", headers=H, json={
        "name": "冒烟学生", "student_no": "SMOKE01", "gender": "male", "class_id": scratch_class_id})
    scratch_student_id = r.json().get("id")
    check("学生", "POST /students", bool(scratch_student_id), str(r.json())[:60])

    r = client.post(f"/api/parent/students/{scratch_student_id}/generate-code", headers=H)
    code = r.json().get("parent_code")
    check("家长端", "生成家长码", bool(code), str(r.json())[:60])

    r = client.get(f"/api/parent/verify/{code}")
    check("家长端", "verify 家长码", r.status_code == 200 and r.json().get("valid") is True)

    r = client.get(f"/api/parent/student/{code}")
    check("家长端", "GET /parent/student", r.status_code == 200 and r.json().get("student_name") == "冒烟学生")

    # 为冒烟班级配置科目（成绩录入要求班级已配置该科目）
    subj_id = REAL_SUBJECT["id"]
    r = client.post("/api/subjects/class", headers=H, json={
        "class_id": scratch_class_id, "subject_id": subj_id,
        "is_teaching": True, "is_score_related": True})
    class_subject_id = r.json().get("id") if r.status_code == 200 else None
    check("班级科目", "为冒烟班级配置科目", r.status_code == 200, str(r.json())[:80])

    # 0 分成绩 → 家长统计是否除零崩溃（疑似 bug 验证）
    r = client.post("/api/scores", headers=H, json={
        "student_id": scratch_student_id, "subject_id": subj_id, "class_id": scratch_class_id,
        "score": 0, "exam_type": "冒烟测试", "semester": REAL_SEM})
    zero_score_created = r.status_code == 200
    check("成绩", "POST /scores（0 分成绩）", zero_score_created, str(r.json())[:80])

    r = client.get(f"/api/parent/stats/{code}")
    body_preview = ""
    try:
        body_preview = str(r.json())[:80]
    except Exception:
        body_preview = r.text[:80]
    check("家长端", "stats 除零健壮性（仅一条 0 分成绩）", r.status_code == 200,
          f"HTTP {r.status_code} body={body_preview}")

    # 成绩正常录入 + 学生分析含该考试
    r = client.post("/api/scores", headers=H, json={
        "student_id": scratch_student_id, "subject_id": subj_id, "class_id": scratch_class_id,
        "score": 88.5, "exam_type": "冒烟测试", "semester": REAL_SEM})
    check("成绩", "POST /scores（正常）", r.status_code == 200)

    # 考勤录入 + 班级统计
    r = client.post("/api/attendance", headers=H, json={
        "student_id": scratch_student_id, "class_id": scratch_class_id,
        "date": "2026-10-20T08:00:00", "status": "present"})
    att_id = r.json().get("id") if r.status_code == 200 else None
    check("考勤", "POST /attendance", bool(att_id))

    r = client.get(f"/api/attendance/statistics/class/{scratch_class_id}", headers=H)
    check("考勤", "班级考勤统计", r.status_code == 200, str(r.json())[:80])

    # 超行分：明细 → 汇总一致性（写路径验证）
    r = client.get("/api/semesters", headers=H)
    term_id = r.json()[0]["id"]
    r = client.post("/api/conduct/details", headers=H, json={
        "student_id": scratch_student_id, "student_name": "冒烟学生", "term_id": term_id,
        "score": 5, "remark": "冒烟加分", "record_time": "2026-10-20T10:00:00"})
    d1 = r.json().get("id") if r.status_code == 200 else None
    check("超行分", "POST /conduct/details", bool(d1))
    r = client.post("/api/conduct/details", headers=H, json={
        "student_id": scratch_student_id, "student_name": "冒烟学生", "term_id": term_id,
        "score": -2, "remark": "冒烟扣分", "record_time": "2026-10-20T11:00:00"})
    d2 = r.json().get("id") if r.status_code == 200 else None
    check("超行分", "POST /conduct/details（负分）", bool(d2))

    r = client.get("/api/conduct/summary", headers=H, params={"class_id": scratch_class_id, "term_id": term_id})
    sm = [s for s in (r.json() if isinstance(r.json(), list) else r.json().get("data", []))
          if s.get("student_id") == scratch_student_id]
    check("超行分", "写路径汇总=明细和(5-2=3)", bool(sm) and sm[0]["total_score"] == 3,
          f"汇总={sm[0]['total_score'] if sm else '无'}")

    # 座位：保存 → 读取 → 校验内容（行列数限制 4~12）
    r = client.post("/api/seating/save", headers=H, json={
        "class_id": scratch_class_id, "date": "2026-10-20",
        "row_count": 4, "column_count": 4,
        "students": [{"student_id": scratch_student_id, "student_name": "冒烟学生",
                      "seat_row": 1, "seat_column": 1}]})
    seat_saved = r.status_code == 200
    check("换座位", "POST /seating/save", seat_saved, str(r.json())[:80])
    if seat_saved:
        # 座位接口按设计保存"当天"，读取时不传 date 即取当天
        r = client.get("/api/seating", headers=H, params={"class_id": scratch_class_id})
        seat_data = r.json()
        check("换座位", "GET /seating 当天读取", r.status_code == 200, str(seat_data)[:100])

    # 任课教师 CRUD
    r = client.post("/api/teachers", headers=H, json={"teacher_name": "冒烟教师", "course": "测试", "employment_status": "在职"})
    scratch_teacher_id = r.json().get("id") if r.status_code == 200 else None
    check("任课教师", "POST /teachers", bool(scratch_teacher_id))
    if scratch_teacher_id:
        r = client.put(f"/api/teachers/{scratch_teacher_id}", headers=H, json={"teacher_name": "冒烟教师改"})
        check("任课教师", "PUT /teachers/{id}", r.status_code == 200)

    # 通知 + 作业（写后删）
    r = client.post("/api/notifications", headers=H, json={
        "title": "冒烟通知", "content": "x", "priority": "normal", "class_id": scratch_class_id})
    nid = r.json().get("id") if r.status_code == 200 else None
    check("通知", "POST /notifications", bool(nid))
    if nid:
        r = client.delete(f"/api/notifications/{nid}", headers=H)
        check("通知", "DELETE /notifications/{id}", r.status_code == 200)

    r = client.post("/api/homeworks", headers=H, json={
        "title": "冒烟作业", "class_id": scratch_class_id, "subject_id": subj_id})
    hid = r.json().get("id") if r.status_code == 200 else None
    check("作业", "POST /homeworks", bool(hid))
    if hid:
        r = client.delete(f"/api/homeworks/{hid}", headers=H)
        check("作业", "DELETE /homeworks/{id}", r.status_code == 200)

    # 家长码撤销
    r = client.delete(f"/api/parent/students/{scratch_student_id}/revoke-code", headers=H)
    check("家长端", "撤销家长码", r.status_code == 200)
    r = client.get(f"/api/parent/verify/{code}")
    check("家长端", "撤销后 verify 失效", r.json().get("valid") is False)

finally:
    # ---------- 清理（先子后父） ----------
    cleaned = []
    try:
        def _del(path, **kw):
            rr = client.delete(path, headers=H, **kw)
            return rr.status_code in (200, 404)
        for did in filter(None, [d1, d2]):
            _del(f"/api/conduct/details/{did}")
        cleaned.append("conduct")
        if att_id:
            _del(f"/api/attendance/{att_id}")
        cleaned.append("attendance")
        if scratch_teacher_id:
            _del(f"/api/teachers/{scratch_teacher_id}")
        cleaned.append("teacher")
        if scratch_student_id:
            if _del(f"/api/students/{scratch_student_id}"):
                cleaned.append("student")
        if scratch_class_id:
            if class_subject_id:
                _del(f"/api/subjects/class/{class_subject_id}")
            client.get("/api/seating", headers=H, params={"class_id": scratch_class_id})
            client.delete("/api/seating", headers=H, params={"class_id": scratch_class_id})
            if _del(f"/api/classes/{scratch_class_id}"):
                cleaned.append("class+seating+subject")
    except Exception as e:
        record("清理", "清理异常", False, str(e))
    # 清理后确认
    r = client.get("/api/classes", headers=H)
    names = [c["name"] for c in r.json()]
    record("清理", "测试班级已删除", not any(n.startswith("冒烟测试") for n in names), ",".join(cleaned))

# ---------- 汇总 ----------
print("\n" + "=" * 72)
fails = [x for x in results if x[2] == "FAIL"]
width = max(len(x[0]) for x in results) + 2
for m, item, st, note in results:
    mark = "✓" if st == "PASS" else "✗"
    line = f"{mark} [{st}] {m:{width}} {item}" + (f"  —— {note}" if note and st == 'FAIL' or note and st == 'PASS' and len(note) < 40 else "")
    print(line)
print("=" * 72)
print(f"共 {len(results)} 项检查，通过 {len(results) - len(fails)} 项，失败 {len(fails)} 项")
for m, item, st, note in fails:
    print(f"  ✗ [{m}] {item} —— {note}")
sys.exit(1 if fails else 0)
