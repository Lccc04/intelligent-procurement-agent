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
- 代码执行在隔离容器中
- 网络隔离、内存限制、执行超时
- 替代 OpenSandbox 的开源方案

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

## 与原项目的对应关系

| 原项目 (DeepAgents + OpenSandbox) | 本项目 (LangGraph + Docker) |
|---|---|
| DeepAgents 框架 | LangGraph (create_react_agent) |
| OpenSandbox | Docker SDK 容器沙箱 |
| Agent Protocol Server | asyncio 异步任务 |
| MongoDB | 本地 JSON 默认模式；设置 `PERSISTENCE_BACKEND=mongo` 切换 MongoDB |
| MCP 工具 | MCP 标准协议 (完全一致) |
| HITL interrupt | LangGraph interrupt() (完全一致) |
| 中间件栈 | LangGraph 节点钩子 (设计一致) |
| Skills 系统 | 目录结构 + 渐进式加载 (设计一致) |

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
