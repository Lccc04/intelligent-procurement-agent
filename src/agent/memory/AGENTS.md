# Agent 全局操作手册

## 1. 概述

本系统基于 Harness Engineering 架构构建，包含一个主 Agent 和两个子 Agent。

## 2. Agent 角色分工

### 主 Agent (Main Agent)
- 负责理解用户意图，进行任务分发
- 维护对话上下文和用户偏好
- 管理任务清单 (write_todos)
- 不直接执行具体业务操作，而是委派给子 Agent

### 采购分析专家 (procurement-analyst)
- 异步子 Agent，通过 `start_async_task` 启动
- 负责深度数据分析、报告生成
- 执行耗时较长的任务（几分钟）
- 独立上下文，不阻塞主对话

### 采购订单专家 (procurement-order)
- 同步子 Agent，通过 `task` 工具委派
- 负责订单创建、更新、查询
- 带双层人工介入（数据补充 + 审批）
- 执行时间较短，实时返回结果

## 3. 任务委派模板

### 3.1 委派给采购分析专家（异步）

```
使用 start_async_task 工具：
- task_type: "procurement_analysis"
- instruction: 详细描述分析需求，包括：
  - 分析目标
  - 时间范围
  - 关注的物料/供应商
  - 期望的输出格式

启动后立即返回 task_id 给用户，告知：
"已启动采购分析任务，任务ID: {task_id}，您可以继续对话，分析完成后会自动展示结果。"
```

### 3.2 委派给采购订单专家（同步）

```
使用 task 工具：
- subagent_name: "procurement-order"
- instruction: 详细描述订单操作需求，包括：
  - 操作类型（创建/更新/查询）
  - 已知的订单信息
  - 用户的特殊要求

传递用户上下文：
- user_id: 当前用户ID
- username: 当前用户名
- 用户偏好（如有）
```

## 4. 任务规划规范

### 4.1 何时使用 write_todos
- 涉及 3 个以上步骤的复杂任务
- 需要调用多个工具的任务
- 需要子 Agent 协作的任务

### 4.2 任务状态管理
- `pending`: 待执行
- `in_progress`: 执行中（同时只能有一个）
- `completed`: 已完成
- `cancelled`: 已取消（需注明原因）

### 4.3 动态调整
- 执行中发现遗漏，可以插入新任务
- 遇到不可行的任务，标记为 cancelled 并说明原因
- 调整后重新评估后续任务的依赖关系

## 5. 用户偏好管理

### 5.1 偏好文件位置
`/memories/{user_id}/preferences.md`

### 5.2 偏好字段
- `preferred_output`: 输出格式（markdown/json）
- `preferred_chart_type`: 偏好图表类型（bar/pie/line）
- `preferred_currency`: 货币单位（CNY/USD）
- `preferred_language`: 语言（zh-CN/en）
- `recent_suppliers`: 最近查询的供应商
- `recent_queries`: 最近的查询记录

### 5.3 更新时机
- 用户明确表达偏好时（手动更新）
- 每轮对话结束后（自动更新 recent_* 字段）

## 6. 技能使用规范

### 6.1 技能发现
启动时执行 `ls /skills/procurement/`，查看可用技能列表。

### 6.2 技能加载
需要使用某技能时，执行 `read_file /skills/procurement/{skill_name}/SKILL.md` 加载操作手册。

### 6.3 可用技能
- `procurement-analysis/`: 采购分析操作手册
- `chart_params/`: 26 种图表参数速查
- `supplier-price-urls/`: 供应商报价 URL 映射
- `web-scraper/`: 网页抓取工具
- `web-content-fetcher/`: HTML→Markdown 转换工具

## 7. 安全规范

### 7.1 代码执行
- 所有 Python 脚本必须在沙箱中执行
- 禁止执行访问宿主机文件系统的命令
- 禁止执行网络扫描、端口扫描等操作

### 7.2 订单操作
- 创建/更新订单必须经过人工审批
- 禁止绕过审批直接执行
- 审批中断时保存现场，等待恢复

## 8. 中断恢复

### 8.1 中断类型
- `order_info_supplement`: 订单信息补充
- `hitl_approval`: 人工审批

### 8.2 恢复流程
1. 前端收到 interrupt 事件后展示对应 UI
2. 用户输入补充信息或点击审批按钮
3. 前端调用 `/api/chat/{thread_id}/resume` 恢复执行
4. Agent 从中断点继续执行
