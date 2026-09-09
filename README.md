# 智能采购助手 - Harness Engineering Agent

基于 Harness Engineering 架构的企业级智能采购 Agent 系统。

## 项目简介

这是一个能与企业 ERP 系统对话的 AI 采购助手。用户用自然语言描述需求，Agent 自动拆解任务、调用 ERP 接口、进行数据分析、生成图表报告，并在关键节点支持人工审批。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue/HTML)                        │
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
│  │              中间件栈 (8个)                           │ │
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
- 代码执行在隔离容器中
- 网络隔离、内存限制、执行超时
- 替代 OpenSandbox 的开源方案

## 目录结构

```
procurement-agent/
├── src/
│   ├── api_view/                    # Web 层 - FastAPI
│   │   ├── web_main.py             # 应用入口
│   │   ├── web_config.py           # 数据库配置
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
│   │   │   ├── async_tools.py      # 异步任务
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
│   └── index.html                   # 前端页面
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

## 与原项目的对应关系

| 原项目 (DeepAgents + OpenSandbox) | 本项目 (LangGraph + Docker) |
|---|---|
| DeepAgents 框架 | LangGraph (create_react_agent) |
| OpenSandbox | Docker SDK 容器沙箱 |
| Agent Protocol Server | asyncio 异步任务 |
| MongoDB | 内存存储 (可无缝替换为 MongoDB) |
| MCP 工具 | MCP 标准协议 (完全一致) |
| HITL interrupt | LangGraph interrupt() (完全一致) |
| 中间件栈 | LangGraph 节点钩子 (设计一致) |
| Skills 系统 | 目录结构 + 渐进式加载 (设计一致) |

## 扩展方向

1. **接入真实 ERP**：将 mock_erp 替换为真实 Java ERP 接口
2. **MongoDB 持久化**：将 web_config.py 的 InMemoryDB 替换为 MongoDB
3. **Docker 沙箱**：实现 backends/ 下的沙箱管理，支持代码执行
4. **更多子 Agent**：在 subagents/configs/ 下添加 YAML 配置即可扩展
5. **前端优化**：将 HTML 替换为 Vue + Element Plus，支持图表渲染
6. **向量检索**：接入 RAG，支持采购文档知识库问答

## 与飞书方案文档的差异

飞书文档《基于Harness Engineering架构的企业实战项目》描述的是较完整的原版方案；当前仓库是一个可以直接启动的简化实现。两者的核心理念一致，但底层实现并不完全相同。

| 能力 | 飞书文档中的方案 | 当前仓库状态 |
|---|---|---|
| Agent 框架 | DeepAgents / `create_deep_agent` | LangGraph / `create_react_agent` |
| 文件系统 | `CompositeBackend` 路由临时文件、用户记忆和持久化技能 | 已有 Docker 沙箱代理骨架，但没有接入主 Agent 的文件工具链 |
| 沙箱 | OpenSandbox，支持预热、认领、故障热替换和技能同步 | Docker SDK 基础版本；可创建、执行、检查和销毁，但生命周期状态、预热池和热替换仍需完善 |
| 数据存储 | `StoreBackend` + MongoDB，保存用户记忆和技能 | `InMemoryDB`，服务重启后会丢失会话和偏好；MongoDB 配置已预留 |
| ERP 工具 | MCP 连接 Java ERP，另有图表、搜索等工具 | 主 Agent 当前直接加载本地 Mock 工具；MCP 客户端和 Mock ERP 接口已保留 |
| 采购分析 | 独立 Agent Protocol Server 后台运行，使用真实分析流程 | `asyncio.create_task` 模拟后台任务，返回模拟报告和图表数据 |
| 子 Agent | `procurement-analyst` 和 `procurement-order` 按完整配置弹性加载 | YAML 加载和订单子 Agent 可用；采购分析子 Agent 被强制走模拟异步任务 |
| Skills | 渐进式披露、下载、创建、测试、分配、持久化和恢复 | 已有 SKILL.md、提示词和部分同步骨架；下载、分配、持久化恢复尚未实现 |
| 中间件 | 8 个中间件覆盖健康检查、上下文、技能、摘要、记忆和熔断 | 相关模块基本存在，但没有完整挂载到 LangGraph 执行链 |
| HITL | `request_order_info` + `interrupt_on` 双层中断 | 已实现信息补充中断和审批恢复接口；订单工具审批链还需要进一步端到端验证 |
| 前端 | 支持异步任务轮询、报告和图表展示 | 原生 HTML 聊天页；SSE 已修复，可显示流式回答，但还没有真正渲染图表 |

### 目前最明显的代码差异

1. 飞书文档中的 `CompositeBackend`、`StoreBackend`、真实 MongoDB 和 OpenSandbox，在当前仓库中分别对应简化的内存数据库、Docker 封装和若干未接入的中间件骨架。
2. 飞书文档中的 `Agent Protocol Server` 是独立后台 Agent 服务；当前项目的 `start_async_task` 只是进程内异步任务，服务重启后任务状态会丢失。
3. 飞书文档提到的 `web_search`、`chart_generator`、`assign_skill`、`download_sandbox_file` 等工具，当前仓库没有完整实现。
4. 当前 `main_agent.py` 虽然保留了 MCP 客户端，但实际初始化时调用的是 `get_all_mock_tools()`，因此默认不会访问 Mock ERP HTTP 服务，更不会访问真实 Java ERP。
5. 部分 YAML 配置引用了 `execute_code`、`write_file`、`read_file` 等工具名，但当前子 Agent 的可用工具集合主要是 Mock ERP 工具，工具配置和实际运行能力还没有完全对齐。

## 结合本项目的扩展落地顺序

建议按照“先真实可用，再增强架构”的顺序推进：

1. **真实 ERP 适配层**：保留 Python Agent，不要求改成 Java。通过 REST、SOAP、WebSocket 或消息队列调用 Java ERP；在 `mcp_server/tools/` 中把 Mock 数据替换成 ERP API 适配器，并保留 Mock 模式用于本地测试。
2. **MongoDB 持久化**：先替换会话、消息和用户偏好的 `InMemoryDB`，再把 `/memories/{user_id}/` 和技能数据纳入统一存储。这样才能支持服务重启后恢复对话、偏好和异步任务。
3. **真正的异步分析服务**：把当前 `asyncio.create_task` 抽成独立的 Agent Protocol 或任务服务，保存 `task_id`、状态、进度、错误和结果，前端再轮询或改用 SSE 推送。
4. **Docker 沙箱接入 Agent**：补齐代码执行、文件读写、文件下载、超时、资源限制、网络策略和故障热替换，并把 `execute_code` 等工具真正挂载到采购分析子 Agent。
5. **子 Agent 和 Skills 扩展**：继续使用 YAML 声明式配置，但增加工具名校验、配置版本、权限范围和启动时自检，避免配置写了工具而运行时找不到。
6. **前端升级**：当后端接口稳定后再迁移 Vue + Element Plus；优先加入异步任务进度、Markdown 报告下载、供应商/库存图表和审批操作记录。
7. **RAG 接口预留**：新增统一的 `knowledge_search(query, filters, top_k)` 工具接口，先返回“知识库未配置”的明确结果；后续再接向量数据库、文档解析、切片、Embedding 和采购制度权限过滤。

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
