# 智能采购助手 - Harness Engineering Agent

基于 Harness Engineering 架构的企业级智能采购 Agent 系统。

## 项目简介

这是一个能与企业 ERP 系统对话的 AI 采购助手。用户用自然语言描述需求，Agent 自动拆解任务、调用 ERP 接口、进行数据分析、生成图表报告，并在关键节点支持人工审批。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Element Plus)             │
│              聊天界面 + 中断审批 + 异步任务                │
└────────────────────────┬────────────────────────────────┘
                         │ SSE 流式
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI Web 层                           │
│    /api/chat/stream  /api/chat/resume  /api/history     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Agent 核心层 (LangGraph)                 │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 主 Agent  │  │ 采购分析专家  │  │  采购订单专家     │  │
│  │ (调度)    │  │ (异步子Agent) │  │ (同步子Agent+HITL)│  │
│  └──────────┘  └──────────────┘  └──────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              中间件栈 (7个)                           │ │
│  │  健康检查 → 上下文注入 → 技能同步 → 摘要压缩         │ │
│  │  → 记忆更新 → 熔断保护 → 调用限制                     │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ MCP 协议
┌────────────────────────▼────────────────────────────────┐
│                MCP Server 网关层                          │
│     供应商工具  物料工具  订单工具  库存工具              │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│              ERP 后端 (Mock/Java)                         │
│         供应商  物料  订单  库存 数据                      │
└─────────────────────────────────────────────────────────┘
```

## 核心亮点

### 1. Multi-Agent 架构
- 主 Agent 负责任务理解和分发
- 采购分析专家：异步执行，不阻塞主对话
- 采购订单专家：同步执行，带双层人工介入

### 2. HITL 双层中断机制
- 第一层：订单信息不完整时请求补充
- 第二层：订单执行前人工审批
- 基于 LangGraph interrupt() 实现，支持中断后无缝恢复

### 3. MCP 工具网关
- 基于 Model Context Protocol 标准
- 封装 9+ 个 ERP 业务工具
- 支持工具动态加载和子 Agent 工具隔离

### 4. 任务规划能力
- write_todos 工具实现结构化任务清单
- 支持状态管理、依赖关系、动态重规划
- 长时任务抗遗忘

### 5. 用户偏好长期记忆
- 自动提取用户偏好（图表类型、货币、语言等）
- 跨会话持久化
- 每轮对话自动注入上下文

### 6. 异步任务调度
- 耗时分析任务后台执行
- 前端基于 task_id 轮询状态
- 不阻塞主对话链路

### 7. Docker 安全沙箱
- 代码执行支持隔离容器
- 支持网络策略、内存限制和执行超时
- 通过环境变量控制是否启用沙箱执行

## 目录结构

```
procurement-agent/
├── src/
│   ├── api_view/                    # Web 层 - FastAPI
│   │   ├── web_main.py             # 应用入口
│   │   ├── web_config.py           # 持久化入口（文件/MongoDB）
│   │   ├── persistence.py          # 本地 JSON / MongoDB 适配器
│   │   ├── agent_loader.py         # Agent 单例管理
│   │   └── api/
│   │       ├── chat.py             # SSE 流式对话 + 中断恢复
│   │       └── history.py          # 历史会话管理
│   ├── agent/                       # Agent 核心层
│   │   ├── main_agent.py           # 主 Agent 入口
│   │   ├── config.py               # 全局配置
│   │   ├── schema.py               # 数据模型
│   │   ├── env_utils.py            # 环境变量
│   │   ├── log_utils.py            # 日志工具
│   │   ├── memory/
│   │   │   ├── AGENTS.md           # Agent 操作手册
│   │   │   └── prompts.py          # 系统提示词
│   │   ├── subagents/
│   │   │   ├── loader.py           # YAML 配置加载
│   │   │   └── configs/
│   │   │       ├── procurement_analyst.yaml
│   │   │       └── procurement_order.yaml
│   │   ├── middlewares/             # 中间件栈
│   │   ├── tools/                   # 工具层
│   │   │   ├── mcp_client.py       # MCP 工具加载
│   │   │   ├── mock_tools.py       # 本地 Mock 工具
│   │   │   ├── planning_tools.py   # write_todos 规划
│   │   │   ├── hitl_tools.py       # HITL 人工介入
│   │   │   ├── async_tools.py      # 持久化异步任务、报告、图表
│   │   │   ├── file_tools.py       # 主 Agent 文件工具链
│   │   │   ├── skill_tools.py      # 技能下载/创建/测试/分配/持久化
│   │   │   ├── chart_tools.py      # ECharts 结构化图表
│   │   │   ├── tool_registry.py    # 统一工具注册
│   │   │   ├── knowledge_tools.py  # RAG 接口预留
│   │   │   └── subagent_tools.py   # 子 Agent 委派
│   │   └── backends/                # 沙箱后端
│   ├── mcp_server/                  # MCP 网关层
│   │   ├── server_main.py
│   │   ├── server_config.py
│   │   ├── http_base.py
│   │   └── tools/
│   ├── mock_erp/                    # Mock ERP 服务
│   │   └── main.py
│   └── skills/                      # 技能库
├── frontend/
│   ├── index.html                   # Vue 3 + Element Plus 入口
│   └── app.js                       # 组件化聊天、审批、任务和图表
├── requirements.txt
├── .env.example
├── start.bat
└── README.md
```

## 快速开始

### 1. 环境要求
- Python 3.10+
- pip

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
copy .env.example .env
# 编辑 .env，填入你的 LLM API Key
```

### 4. 启动服务
```bash
# Windows
start.bat

# 或手动启动
python -m src.api_view.web_main
```

### 5. 访问
- 前端页面：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs

## 使用示例

### 采购分析
> "帮我分析一下制动系统物料的价格趋势，对比各家供应商的报价"

Agent 会：
1. 启动异步采购分析任务
2. 查询供应商和物料数据
3. 生成分析报告和图表
4. 后台执行，前端轮询展示结果

### 创建订单
> "创建一个采购订单，采购100套前刹车片"

Agent 会：
1. 委派给采购订单专家
2. 提取订单信息，校验必填字段
3. 如信息不全，请求补充
4. 信息齐全后，触发人工审批
5. 审批通过后执行订单创建

### 数据查询
> "查询库存预警信息，哪些物料库存不足"
> "刹车片的供应商有哪些，评级如何"

## 功能模块与执行链路

### 主 Agent 与 LangGraph 执行链

主 Agent 使用 LangGraph 的 ReAct 执行模式，将用户消息、工具调用、子 Agent 委派、人工中断和恢复操作统一放入同一条可追踪的执行链。每个会话使用独立的 `thread_id`，可以保存消息、会话状态和中断现场。

主 Agent 的职责包括：

- 识别采购查询、分析、订单和文件处理意图
- 按任务复杂度调用同步工具或异步任务工具
- 将订单操作委派给采购订单子 Agent
- 将耗时分析委派到后台任务并返回 `task_id`
- 在工具返回后组织中文 Markdown 回复
- 对供应商、物料、库存和订单事实优先使用 ERP 工具查询，降低幻觉风险

### YAML 子 Agent 配置

子 Agent 位于 `src/agent/subagents/configs/`，通过 YAML 声明名称、职责、工具、提示词和执行模式。启动时动态加载，配置文件发生变化后会根据签名自动刷新实例。

当前内置：

- `procurement-analyst`：采购分析、供应商对比、价格分析和报告生成，支持异步任务
- `procurement-order`：物料信息校验、采购订单创建和更新，支持人工审批

继续增加子 Agent 时，通常只需新增一个 YAML 文件并声明可用工具；工具名会在加载时解析，不需要修改主 Agent 的调度代码。

### ERP 工具与多 ERP 测试数据

项目提供本地 Mock ERP 数据和多个虚拟 ERP 实例，用于在没有真实企业接口的环境中完成完整演示：

- 供应商查询、物料查询、库存查询和订单查询
- 订单创建和订单更新审批
- `erp-central`、`erp-north`、`erp-south` 三个虚拟 ERP
- 不同区域的库存、供应商和价格快照
- ERP 注册表和目录接口，方便后续替换为 REST、SOAP 或 MCP 适配器

本地 Mock 数据只用于开发和测试，业务事实应在接入真实 ERP 后以生产接口返回为准。

### 文件工具链

文件能力已直接挂载到主 Agent 和运行时工具注册表，支持以下操作：

- `list_files`：列出工作区、分析目录、记忆目录和技能目录中的文件
- `read_file`：读取文本文件和技能说明
- `write_file`：更新已有文件
- `create_file`：创建新的报告、脚本或配置文件
- `execute_code`：在配置的沙箱环境中执行代码
- `test_file`：执行文件级测试或语法检查
- `download_sandbox_file`：将沙箱生成的文件登记为附件并下载

文件路径按 `/workspace`、`/analysis`、`/memories`、`/skills` 等逻辑目录管理，避免让 Agent 直接操作任意宿主机路径。

### Skills 技能生命周期

技能以目录和 `SKILL.md` 文件形式管理，支持：

1. 渐进式列出技能，不在每轮对话中加载全部内容
2. 读取技能说明并按需执行
3. 创建技能目录和说明文件
4. 测试技能文件
5. 将技能分配给指定用户
6. 将技能和分配关系持久化
7. 服务重启后恢复已分配技能

### 异步分析、报告与图表

采购分析任务使用持久化任务记录和后台线程池执行。任务状态包含排队、执行中、已完成和失败，并记录进度、阶段、错误信息和结果。

任务结果包括：

- Markdown 分析报告
- 结构化图表数据
- ECharts 可直接渲染的柱状图、饼图或折线图配置
- 生成的 CSV、JSON、Markdown 等附件
- 附件下载地址和持久化元数据

前端通过 `task_id` 轮询任务状态，完成后展示报告和图表，不阻塞主对话窗口。

### 人工审批与审批统计

订单写入采用两层中断流程：

1. 订单信息缺失时，通过 `request_order_info` 请求补充物料、数量或价格
2. 信息完整后，订单工具触发 LangGraph `interrupt()`，等待人工决定
3. 前端展示订单内容、预计金额和审批操作
4. 批准后继续执行 ERP 写入，拒绝或取消则不写入订单
5. 恢复执行后将审批决定写入持久化审计账本

审批统计接口会记录并计算：

- 触发总数
- 待处理、已批准、已拒绝、已取消数量
- 处理率
- 平均响应时间
- 按工具动作分类的触发数量
- 最近审批事件

右侧管理面板会自动刷新统计数据，适合演示订单审批积压、处理效率和不同订单动作的触发情况。

### 持久化与恢复

项目默认使用本地 JSON 文件，开箱即可运行；通过环境变量可以切换 MongoDB。统一持久化接口覆盖：

- 会话和展示消息
- 用户偏好和最近查询
- 异步任务、报告和附件
- 技能分配记录
- 审批事件和响应时间
- LangGraph checkpoint 和中断恢复状态

默认文件位置为 `.agent_runtime/store.json`，该目录已加入 Git 忽略规则，不会进入代码仓库。

## 核心业务流程

### 采购分析流程

```text
用户提出分析需求
        │
        ▼
主 Agent 识别分析意图
        │
        ▼
start_async_task 创建持久化任务
        │
        ▼
后台查询 ERP 数据并生成报告、图表、附件
        │
        ▼
前端轮询 /api/tasks/{task_id}
        │
        ▼
展示报告、图表和下载链接
```

### 订单审批流程

```text
用户提出创建订单
        │
        ▼
订单子 Agent 提取物料、数量、价格和供应商
        │
        ├── 信息不足 ──► 请求用户补充 ──► 恢复执行
        │
        ▼
order_create 触发人工审批中断
        │
        ├── 批准 ──► 写入 ERP 并返回订单号
        ├── 拒绝 ──► 取消操作，不写入 ERP
        └── 取消 ──► 取消操作，不写入 ERP
```

### 文件与技能流程

```text
识别工作目录
        │
        ▼
渐进式加载技能说明
        │
        ▼
读取、创建、测试或执行文件
        │
        ▼
报告保存到 /analysis，技能保存到 /skills
        │
        ▼
登记附件、持久化分配关系并支持恢复
```

## API 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/health` | 查看服务、Agent 和持久化后端状态 |
| `POST` | `/api/chat/stream` | 创建或继续会话，返回 SSE 流式消息 |
| `POST` | `/api/chat/{thread_id}/resume` | 恢复订单补充或人工审批中断 |
| `GET` | `/api/chat/{thread_id}/state` | 查看当前会话和中断状态 |
| `GET` | `/api/history/sessions` | 查询用户历史会话 |
| `GET` | `/api/history/{thread_id}/messages` | 查询会话消息 |
| `GET` | `/api/tasks` | 查询异步任务列表 |
| `GET` | `/api/tasks/{task_id}` | 查询单个任务的进度和结果 |
| `GET` | `/api/approvals/stats` | 查询人工审批统计和最近事件 |
| `GET` | `/api/artifacts` | 查询报告和附件 |
| `GET` | `/api/artifacts/{artifact_id}/download` | 下载指定附件 |
| `GET` | `/api/subagents` | 查看动态加载的子 Agent 配置 |
| `GET` | `/api/erps` | 查看虚拟 ERP 目录 |

### SSE 事件类型

`/api/chat/stream` 和恢复接口会返回以下事件：

- `thread_id`：当前会话 ID
- `token`：模型流式文本片段
- `tool_start`、`tool_args`、`tool_result`、`tool_end`：工具执行过程
- `interrupt`：补充信息或人工审批中断
- `done`：本轮执行结束，包含是否中断
- `error`：执行失败信息

## 配置说明

复制 `.env.example` 为 `.env` 后按需修改：

| 配置项 | 说明 | 默认行为 |
|---|---|---|
| `LLM_MODEL` | 对话模型名称 | `deepseek-chat` |
| `LLM_API_KEY` | 模型 API Key | 必填 |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 | 使用 DeepSeek 地址 |
| `PERSISTENCE_BACKEND` | `file` 或 `mongo` | `file` |
| `PERSISTENCE_FILE` | 本地持久化文件路径 | `.agent_runtime/store.json` |
| `MONGODB_URL` | MongoDB 连接地址 | `mongodb://localhost:27017` |
| `MONGODB_DB` | MongoDB 数据库名 | `procurement_agent` |
| `SANDBOX_ENABLED` | 是否启用容器沙箱 | 按本地配置决定 |
| `SANDBOX_IMAGE` | 沙箱基础镜像 | `python:3.11-slim` |
| `SANDBOX_MEM_LIMIT` | 沙箱内存上限 | `512m` |
| `SANDBOX_TIMEOUT` | 单次执行超时秒数 | `30` |
| `API_HOST`、`API_PORT` | FastAPI 监听地址和端口 | `0.0.0.0:8000` |

### 本地文件持久化

无需额外服务即可运行，适合开发、演示和单机测试：

```env
PERSISTENCE_BACKEND=file
PERSISTENCE_FILE=.agent_runtime/store.json
```

### MongoDB 持久化

MongoDB 可用于多进程部署或需要独立数据服务的环境：

```env
PERSISTENCE_BACKEND=mongo
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=procurement_agent
```

## 测试与质量检查

项目提供针对关键路径的回归测试：

```bash
# 编译检查
python -m compileall -q src

# 运行回归测试
python src/test/regression_test.py

# 前端语法检查
node --check frontend/app.js
```

回归测试覆盖：

- 工具注册和 YAML 子 Agent 配置
- 文件、图表和知识检索工具是否可用
- 订单未审批时不写入 ERP
- 批准后订单正确写入 ERP
- 审批统计和批准、拒绝、取消状态
- 异步任务完成、报告生成和双图表结果
- 空 `thread_id` 的新会话请求校验

## 运行边界与安全建议

- `.env` 只保存在本地，不要提交真实 API Key、数据库密码或 ERP 凭据
- 默认 Mock ERP 用于演示，生产环境需要实现带鉴权、超时、重试和审计的 ERP 适配器
- 订单创建和更新始终保留人工审批，不应通过配置绕过
- 文件执行应启用沙箱，并配置内存、超时、网络和允许目录
- RAG 文档需要按用户、组织和业务权限过滤，避免跨租户检索
- MongoDB 部署时应启用认证、最小权限和备份策略

## 扩展方向

1. **接入真实 ERP**：将 Mock 适配器替换为真实 Java ERP 的 REST/MCP 适配器
2. **MongoDB 持久化**：设置 `PERSISTENCE_BACKEND=mongo`，复用统一持久化接口
3. **Docker 沙箱**：设置 `SANDBOX_ENABLED=true` 后启用隔离代码执行
4. **更多子 Agent**：在 `subagents/configs/` 下添加 YAML 配置即可热加载
5. **前端优化**：Vue 3 + Element Plus + ECharts 已接入，后续可增加鉴权和权限视图
6. **向量检索**：`knowledge_search` 接口已预留，后续接入采购文档向量库

## 结合本项目的扩展落地顺序

建议按照“先真实可用，再增强架构”的顺序推进：

1. **真实 ERP 适配层**：保留 Python Agent，通过 REST、SOAP、WebSocket 或消息队列调用 Java ERP；在 `mcp_server/tools/` 中替换 Mock 适配器，并保留 Mock 模式用于本地测试。
2. **独立异步服务**：将当前持久化线程池拆成 Agent Protocol / 消息队列服务，支持多实例和重试策略。
3. **Docker 沙箱生产化**：补充容器预热池、租约、文件归档、资源配额、审计日志和故障热替换。
4. **RAG 实现**：为 `knowledge_search` 接入文档解析、切片、Embedding、向量数据库和采购制度权限过滤。

### RAG 预留接口建议

RAG 不应直接写死在主 Agent 中，建议抽象为：

```text
knowledge_search(
    query: str,
    user_id: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> {
    "configured": bool,
    "items": [
        {
            "title": str,
            "content": str,
            "source": str,
            "score": float,
        }
    ]
}
```

这样后续无论接 Milvus、pgvector、Elasticsearch 还是 MongoDB Atlas Vector Search，都不需要改主 Agent 的调用方式。

## 许可证

MIT
