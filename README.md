# 班级管理系统 (DD-CLASS)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.4+-42b883.svg)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)

**班主任工作台** —— 面向班主任日常工作的班级管理系统，本地/局域网部署，数据自主可控。

> 本仓库是基于开源项目 [joyapple/DD-CLASS](https://github.com/joyapple/DD-CLASS) 的**深度二开定制版（V4+）**，
> 在原有功能基础上新增了换座位、超行分记录、任课教师管理、班级科目配置、页面访问管理、家长查询端口等定制功能，
> 并重构了统一配置（`.env`）与一键启动（`run.py`）体系。原始开源版遵循 Apache-2.0 协议，本定制版同样开源免费。

---

## 📋 目录

- [系统组成](#系统组成)
- [功能介绍](#功能介绍)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [公网临时访问](#公网临时访问)
- [常见问题](#常见问题)
- [详细文档](#详细文档)
- [使用许可](#使用许可)

---

## 🖥 系统组成

| 组件 | 技术栈 | 默认端口 | 说明 |
|---|---|---|---|
| 后端 API | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL | 8001 | 21 个业务路由 + 自动 API 文档（`/docs`） |
| 班主任端 | Vue 3 + Element Plus + Vite + Pinia + ECharts | 3000 | 管理端主界面（管理员 / 班主任 / 任课教师） |
| 家长端 | Vue 3 + Element Plus + Vite | 5174 | 家长查询界面（凭学生家长码访问，免账号登录） |

**统一配置**：三个服务的地址、端口、数据库连接全部集中在项目根目录 `.env`（模板见 `.env.example`）。
换办公地点 / 换局域网只需修改 `SERVER_IP` 一项并重启服务，详见[配置说明](#配置说明)。

---

## 🎯 功能介绍

### 基础功能
- **用户认证与权限**：JWT 登录；三种角色（管理员 / 班主任 / 任课教师）；班级数据隔离；操作日志
- **学生管理**：学生档案、学号（班级内唯一）、性别/联系方式、Excel 批量导入、按班级筛选
- **成绩管理**：录入/修改/删除、期中/期末/测验多种考试类型、Excel 导入、按学期班级筛选
- **考勤管理**：出勤/缺勤/迟到/请假、日历视图、全班批量登记、Excel 导入、出勤率统计
- **班级与学期**：班级 CRUD、学期管理、数据按学期筛选
- **数据可视化**：Dashboard 统计卡片、班级/学生/科目排名、成绩趋势、考勤率

### 积分系统
- 积分规则配置（考勤/成绩/行为等多类别）、积分排行、发放/扣减积分
- 积分商城（虚拟商品 + 实物商品）、积分兑换与兑换记录
- 积分龙虎榜投屏展示（支持全屏，适合教室大屏）

### 作业与通知
- 作业发布与管理（按班级/科目、截止日期，仅可管理本班作业）
- 通知中心（全校/班级通知、优先级、置顶、已读管理、一键全部已读）

### 家长端口
- 班主任在学生管理页生成/重置 8 位家长码
- 家长凭码查看学生基本信息、历次成绩、班级通知与作业、出勤与成绩统计（手机端适配）

### 二开定制功能 ✨
- **换座位**：可视化拖拽排座、随机排序、导入/导出 Excel、历史座次存档（历史日期只读）
- **超行分记录**：汇总视图 + 加减分明细；汇总总分恒等于明细分值之和，后端自动重算
- **任课教师管理**：教师档案、在职状态、任课信息维护
- **班级科目配置**：每班独立配置科目，`is_score_related`（是否录成绩）与 `is_teaching`（是否授课）相互独立
- **页面访问管理**：按角色（管理员/班主任/任课教师）动态隐藏/恢复页面，便于灰度开放
- **成绩分析**：单学生多维度分析、薄弱科目、分数段分布、班级对比
- **系统设置**：自定义系统名称/Logo/简介/版权、Bing 每日壁纸开关
- **一键启动**：`python run.py` 自动建表 + 种子数据 + 启动；公网模式自动建立 cpolar 隧道
- **安全加固** ✨：SECRET_KEY 弱密钥拒启；家长端接口双层限流（防家长码暴力枚举）；管理员重置密码改为随机临时密码；CORS 收敛为白名单
- **工程化** ✨：Alembic 数据库迁移（`run.py` 自动接入）；统一角色权限判断（`app/permissions.py`）；pytest 自动化回归测试（`tests/`，19 个用例）

---

## 🛠 技术栈

**后端**：FastAPI 0.109 · SQLAlchemy 2.0 · Pydantic 2.5 · pydantic-settings · python-jose（JWT）· passlib + bcrypt 4.0.1 · uvicorn

**前端（班主任端）**：Vue 3.4 · Element Plus · Vite 5 · Vue Router · Pinia · ECharts 5 · xlsx

**前端（家长端）**：Vue 3.4 · Element Plus · Vite 5

**数据库**：PostgreSQL 14+（开发验证环境）

---

## 🚀 快速开始

### 1. 前置要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+（服务已启动）

### 2. 创建数据库

用 `psql` 或 pgAdmin 以超级用户执行：

```sql
CREATE USER ddclass_user WITH PASSWORD 'your_password';
CREATE DATABASE ddclass OWNER ddclass_user;
```

> 表结构无需手工创建，`run.py` 启动时会按 ORM 模型自动建表（幂等，缺啥建啥）。

### 3. 安装依赖

```bash
# 后端（项目根目录）
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 班主任端
cd frontend
npm install

# 家长端
cd ..\parent-portal
npm install
```

> 国内网络可用镜像加速：
> `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
> `npm install --registry=https://registry.npmmirror.com`

### 4. 配置 .env

```bash
copy .env.example .env
```

按实际环境修改：`SERVER_IP`（本机局域网 IP）、`DATABASE_URL` 等，字段含义见[配置说明](#配置说明)。

### 5. 启动服务

```bash
# 后端（自动初始化数据库 + 种子数据 + 启动）
python run.py

# 班主任端（新终端）
frontend\start-frontend.bat        # 或 cd frontend && npm run dev

# 家长端（新终端）
parent-portal\start-parent.bat     # 或 cd parent-portal && npm run dev
```

### 6. 访问系统

| 入口 | 地址 | 凭证 |
|---|---|---|
| 班主任端 | http://localhost:3000 | `admin/admin123`（管理员）、`teacher1/123456`（班主任） |
| 家长端 | http://localhost:5174 | 学生家长码（班主任端「学生管理」生成） |
| API 文档 | http://localhost:8001/docs | Swagger UI，浏览器直接打开 |

局域网内其他设备通过 `http://<SERVER_IP>:<端口>` 访问（需在防火墙放行端口，见[常见问题](#常见问题)）。

> ⚠️ 首次部署后请尽快修改默认密码：管理员可在「用户管理」中重置任意用户密码；每个用户也可在右上角「个人中心」自行修改（需验证旧密码）。

---

## ⚙️ 配置说明

所有配置集中在**根目录 `.env`**（复制 `.env.example` 得到）：

| 字段 | 默认值 | 说明 |
|---|---|---|
| `SERVER_IP` | `192.168.1.7` | 本机局域网 IP，**换网络唯一要改的项**（仅用于启动提示与局域网访问地址） |
| `BACKEND_HOST` / `BACKEND_PORT` | `0.0.0.0` / `8001` | 后端监听地址/端口 |
| `FRONTEND_HOST` / `FRONTEND_PORT` | `0.0.0.0` / `3000` | 班主任端监听地址/端口 |
| `PARENT_HOST` / `PARENT_PORT` | `0.0.0.0` / `5174` | 家长端监听地址/端口 |
| `DATABASE_URL` | — | PostgreSQL 连接串（注意密码避免 `$` 和引号） |
| `SECRET_KEY` | — | JWT 签名密钥，**必填**：为空或保留模板默认值时后端拒绝启动 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 登录令牌有效期（24 小时） |
| `CORS_ORIGINS` | 空 | 额外允许的跨域来源（逗号分隔）；默认已放行两个前端的常用地址，一般无需填写 |
| `PUBLIC_ACCESS` | `false` | `true` 时启动自动建立 cpolar 公网隧道（仅映射两个前端端口） |
| `CPOLAR_AUTHTOKEN` | 空 | cpolar 认证令牌，仅公网模式需要 |

两个前端的 Vite 代理固定转发到本机 `127.0.0.1:8001`，**换局域网 IP 不需要改前端**。
修改 `.env` 后必须完全重启对应服务（uvicorn `--reload` 只监视 `.py` 文件变化）。

### run.py 常用参数

| 参数 | 说明 |
|---|---|
| （无参数） | 初始化数据库 + 启动服务 |
| `--reload` | 开发模式热重载 |
| `--host x.x.x.x` / `--port 9000` | 临时覆盖 .env 的监听地址/端口 |
| `--init-only` | 仅初始化数据库，不启动服务 |
| `--reset-db` | ⚠️ 清空数据库后重建，**会删除全部数据** |
| `--no-xlsx` | 初始化时跳过「七下期末.xlsx」种子数据 |

种子数据（幂等，不覆盖已有数据）：`admin` / `teacher1` 账号、班级「管理班级」、13 个标准科目（8 计分 + 5 等级）、学期「2026-2」、从根目录 `七下期末.xlsx` 导入学生与期末成绩。

### 数据库迁移（Alembic）

表结构由 Alembic 管理，`run.py` 启动时自动处理（新库建表后登记版本，已有库执行增量迁移）。
修改 `app/models.py` 后生成并应用迁移：

```bash
alembic revision --autogenerate -m "说明改了什么"   # 检查生成的脚本后提交
alembic upgrade head                                # 应用到数据库
```

### 运行测试

```bash
python -m pytest        # 自动使用 tests/_test.db（SQLite），不影响真实数据库
```

覆盖：认证链路、随机重置密码、家长端限流、SECRET_KEY 守卫、权限判断统一模块。

---

## 📁 项目结构

```
DD-CLASS/
├── app/                        # 后端应用（FastAPI）
│   ├── routers/                # 21 个 API 路由模块
│   │   ├── auth.py             # 认证（登录/注册/个人中心）
│   │   ├── students.py         # 学生管理（含 Excel 批量导入）
│   │   ├── scores.py           # 成绩管理
│   │   ├── attendance.py       # 考勤管理
│   │   ├── seating.py          # 换座位
│   │   ├── conduct.py          # 超行分（汇总 + 明细）
│   │   ├── teachers.py         # 任课教师
│   │   ├── subjects.py         # 科目 + 班级科目配置
│   │   ├── points.py           # 积分系统
│   │   ├── parent.py           # 家长端口 + 家长码管理
│   │   ├── page_access.py      # 页面访问配置
│   │   └── ...                 # classes/dashboard/users/semesters/logs/
│   │                           # homework/notifications/analytics/settings
│   ├── models.py               # ORM 模型（22 张表）
│   ├── schemas.py              # Pydantic 模型
│   ├── auth.py                 # JWT 认证逻辑
│   ├── permissions.py          # 角色权限判断
│   ├── services.py             # 业务服务层（操作日志）
│   ├── config.py               # 配置（读取根目录 .env）
│   ├── database.py             # 数据库连接
│   └── main.py                 # 应用入口
├── frontend/                   # 班主任端（Vue 3 + Element Plus）
│   └── src/views/              # 22 个页面（Dashboard/学生/成绩/换座位/积分…）
├── parent-portal/              # 家长端（Vue 3）
│   └── src/views/              # 登录/首页/成绩/作业/通知
├── alembic/                    # 数据库迁移（versions/ 存放迁移脚本）
├── tests/                      # pytest 自动化测试（SQLite 隔离环境）
├── tools/cpolar/               # cpolar 便携版（不入库，公网模式用，需自行下载）
├── run.py                      # 一键启动脚本（初始化 + 启动后端）
├── alembic.ini                 # Alembic 配置
├── pytest.ini                  # pytest 配置（只收集 tests/）
├── 七下期末.xlsx                # 种子数据：学生与期末成绩
├── requirements.txt            # Python 依赖
├── .env.example                # 配置模板（复制为 .env 使用）
├── 部署指南.md                  # 详细部署 / API / 页面 / FAQ 文档
└── start-backend.bat           # Windows 快捷启动
```

---

## 📚 API 文档

启动后端后访问：

- **Swagger UI**：http://localhost:8001/docs
- **ReDoc**：http://localhost:8001/redoc

主要接口：

| 模块 | 方法 | 端点 |
|---|---|---|
| 认证 | POST | `/api/auth/login` |
| 班级 | GET | `/api/classes` |
| 学生 | GET / POST / DELETE | `/api/students` `/api/students/batch` |
| 成绩 | GET / POST | `/api/scores` `/api/scores/batch` |
| 考勤 | POST | `/api/attendance/class-batch` |
| 积分 | GET / POST | `/api/points/ranking` `/api/points/students/{id}/add` |
| 换座位 | GET / POST | `/api/seating` `/api/seating/save` |
| 超行分 | CRUD | `/api/conduct/details` |
| 家长 | GET | `/api/parent/verify/{parent_code}` 等 |

完整接口清单（含权限说明）见 [部署指南.md](./部署指南.md)。

---

## 🌐 公网临时访问

仅限本地/局域网使用时无需任何配置。如需临时远程测试（无需公网 IP）：

1. 注册 cpolar 账号（https://www.cpolar.com），在 dashboard 复制 authtoken
2. `.env` 中设置 `PUBLIC_ACCESS=true` 并填入 `CPOLAR_AUTHTOKEN`
3. 确认本机有 cpolar 可执行文件（PATH 中可用，或从官网下载放到 `tools\cpolar\cpolar.exe`——该二进制已不随仓库分发）
4. 重启 `python run.py`（自动为两个前端建立隧道，控制台打印公网地址）
5. 照常启动两个前端，把地址发给远程用户

> 仅暴露 3000/5174 两个前端端口，后端与数据库不直接暴露公网；免费版地址随机变化、限速约 1Mbps；测试完毕请改回 `false` 并重启。

---

## ❓ 常见问题

**1. 登录提示 500 / bcrypt 报错？**
`bcrypt` 必须使用 4.0.1：`pip install bcrypt==4.0.1`

**2. 端口被占用？**
`netstat -ano | findstr :8001` 找到进程后 `taskkill /PID <PID> /F`。Windows 下多个 uvicorn 残留进程会导致请求路由异常，务必先清理。

**3. 修改 .env 不生效？**
`.env` 在服务启动时读取，必须完全重启（`--reload` 只监视 `.py`）。

**4. 页面 401 自动跳登录页？**
令牌过期（默认 24 小时）或 localStorage 残留旧会话，重新登录即可。

**5. 换了办公地点 / 局域网 IP 变了？**
只改 `.env` 的 `SERVER_IP`，完全重启后端。前端代理走本机 127.0.0.1 不受影响。

**6. 局域网其他设备打不开？**
Windows 防火墙需放行 8001/3000/5174 端口（管理员 PowerShell）：

```powershell
netsh advfirewall firewall add rule name="DD-CLASS-Backend" dir=in action=allow protocol=TCP localport=8001
netsh advfirewall firewall add rule name="DD-CLASS-Frontend" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="DD-CLASS-Parent" dir=in action=allow protocol=TCP localport=5174
```

**7. 启动报错「SECRET_KEY 未配置或仍为模板默认值」？**
安全守卫：`.env` 缺失 `SECRET_KEY` 或仍是模板占位值时后端拒绝启动。按报错信息中给出的随机密钥示例填入 `.env` 后重启即可。

**8. 家长端提示「访问过于频繁 / 校验失败次数过多」？**
家长端接口的暴力枚举防护被触发（同一客户端短时间大量输错家长码，或全局失败次数达上限）。通常等 1～15 分钟自动解除；正常使用不会触发。

**9. 数据库改了表结构怎么生效？**
用 Alembic 生成迁移脚本并应用：`alembic revision --autogenerate -m "说明"` → 检查 `alembic/versions/` 下生成的脚本 → `alembic upgrade head`。直接改 `app/models.py` 不会自动改已有数据表。

更多问题（忘记密码、Excel 导入、公网模式排障等）见 [部署指南.md](./部署指南.md)。

---

## 📖 详细文档

- **[部署指南.md](./部署指南.md)** —— 数据库创建、前后端部署、全部 API 清单、22 个页面功能说明、公网访问、FAQ
- **API 在线文档** —— 启动后端后访问 `/docs`

---

## 📄 使用许可

本项目基于 **Apache License 2.0**，与原开源项目 [joyapple/DD-CLASS](https://github.com/joyapple/DD-CLASS) 一致。
允许自由使用、修改和分发；商业使用请注明原作者和出处。详见 [LICENSE](./LICENSE)。

第三方组件：FastAPI (MIT) · Vue.js (MIT) · Element Plus (MIT) · SQLAlchemy (MIT) · ECharts (Apache-2.0)。

---

*Made with ❤️ based on [joyapple/DD-CLASS](https://github.com/joyapple/DD-CLASS)*
