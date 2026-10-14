# DD-CLASS 班级管理系统 —— 项目长期记忆

> 本地/局域网部署的班级管理系统（"班主任工作台"）。源于开源项目 github.com/joyapple/DD-CLASS，经深度定制至 V4+。用户为开发者/使用者本人，中文交流。

## 架构与端口

| 组件 | 技术栈 | 端口 | 说明 |
|---|---|---|---|
| 后端 app/ | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL | 8001 | 21 个 router，入口 main.py；docs 在 /docs |
| 班主任端 frontend/ | Vue3 + Element Plus + Vite + Pinia + ECharts | 3000 | 23 个视图，默认页 /dashboard |
| 家长端 parent-portal/ | Vue3 + Element Plus + Vite（无 Pinia） | 5174 | 凭 8 位家长码访问，无 token |

- 双前端 vite 代理 /api → 本机 127.0.0.1:8001，换局域网 IP 不用改前端
- 端口/数据库等全部配置集中在**根目录 .env**（模板 .env.example）；`SERVER_IP` 是换网络唯一要改的项，改后必须完全重启
- JWT 认证（python-jose + passlib/bcrypt，bcrypt 锁 4.0.1）

## 启动方式

- 后端：`python run.py`（自动建表+种子+启动；参数 --reload/--init-only/--reset-db/--no-xlsx/--host/--port）；start-backend.bat 同效
- 前端：`frontend\start-frontend.bat`、`parent-portal\start-parent.bat` 或各自 `npm run dev`
- 公网临时访问：.env `PUBLIC_ACCESS=true` + `CPOLAR_AUTHTOKEN`，run.py 自动起 cpolar 隧道（仅映射两个前端；便携版在 tools/cpolar/）；vite.config.js 已内置 cpolar 域名白名单 allowedHosts
- 默认账号：admin/admin123、teacher1/123456；一键重置密码固定为 123456789

## 数据模型（app/models.py，22 表）

users / classes / students / subjects / scores / attendances / semesters / operation_logs
积分系：point_rules / student_points / point_records / point_items / point_exchanges
业务扩展：system_settings / homeworks / notifications / notification_reads
定制功能：seating_chart（换座位）/ summary_conduct_scores + detail_conduct_scores（超行分）/ teachers（任课教师）/ class_subjects（班级科目配置）/ page_access_configs（页面访问配置）

## 权限体系

- 角色：admin / class_teacher（班主任，绑定 class_id）/ teacher（任课教师）
- 后端：app/permissions.py + `app/routers/classes.py::get_accessible_class_ids`（班级数据隔离，admin 除外）
- 前端双重页面控制：路由 `requiresAdmin` 硬限制 + PageAccessConfig 按角色软隐藏（软配置可防锁死）

## 关键业务规则（改动前必读）

1. **学号班级内唯一**（uq_student_class_no）。批量导入必须用内存 set 拦截批内重复——SessionLocal autoflush=False，db.query 看不到本批未提交记录，否则 commit 时唯一约束冲突导致整批回滚
2. **删除学生**需同事务级联清理：DetailConductScore、SummaryConductScore、SeatingChart、PointExchange、PointRecord、StudentPoint、Attendance、Score（后台已实现，勿只删本体）
3. 成绩可录科目由 ClassSubject.is_score_related 控制；is_teaching 与其相互独立
4. **超行分**：汇总总分恒等于明细分值之和，明细增删改后后端自动重算汇总
5. **座位表**：唯一约束 (class_id, created_date, student_id)；student_id 可为空（Excel 导入仅存姓名快照）；历史日期的座次只读不可改
6. 密码：普通用户在「个人中心」改（需验证旧密码，且会同步 teachers 表同名记录）；管理员可在用户管理直接改或重置
7. 科目改名会同步更新成绩表/授课表旧名；被引用的科目/教师禁止删除

## 种子数据（run.py 初始化，幂等不覆盖已有数据）

admin/teacher1 账号 → 班级「管理班级」（七年级）→ 13 科目（8 计分：语文数学英语生物地理道德与法治历史体；5 等级：音美信口书）→ 学期 2026-2 → 从根目录 `七下期末.xlsx` 导入学生与期末成绩（考试日期 2026-06-30，含常量配置在 run.py 头部）

## 文档与历史

- 文档以 **部署指南.md** 为准（V3+ 定制版：端口/API/22 页面/FAQ/公网 cpolar）；README.md 是原开源版描述，滞后（缺换座位、超行分、任课教师、页面访问管理等）
- Git 历史：V0→V4 + "数据库重构之前"，HEAD=434c772
- **未提交改动**（用户用其他 coding 工具所做，尚未 commit）：app/routers/students.py + frontend/src/views/Students.vue——删学生级联清理、批量导入批内查重/学号必填、Excel 表头校验与空学号行提示、删除确认文案增强、区分 cancel/close
- 文档状态（2026-10-14 更新）：README.md 已重写为二开定制版实际状态（原开源版描述已废弃，引用的 init_db.py/migrate_v2.py 等旧脚本不存在）；部署指南.md 为主线文档（版本标注已对齐 V4+）
- 仓库清理（2026-10-14，git rm 已暂存未 commit）：app/dd_class/（26MB 旧 venv，曾被 git 跟踪）、app/routers/students_batch_temp.py（无人引用）、setup_test_data.py；根目录 test_*.py 共 11 个未被 git 跟踪（仅存在于磁盘，被 .gitignore 的 test_*.py 规则挡住），用户可能仍在手工使用，勿删
- .gitignore 已重写：.env 排除但保留 .env.example（negation 规则）、.venv/、python/node 缓存、uploads/ 等
- 未提交改动：app/routers/students.py + frontend/src/views/Students.vue + README.md + .gitignore + 部署指南.md + 上述删除
