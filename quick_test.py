"""快速验证测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

print("=" * 50)
print("测试 1: Mock 工具加载")
print("=" * 50)
from agent.tools.mock_tools import get_all_mock_tools
tools = get_all_mock_tools()
print(f"✅ 加载 {len(tools)} 个工具")
for t in tools:
    print(f"   - {t.name}")

print("\n" + "=" * 50)
print("测试 2: 子 Agent 配置加载")
print("=" * 50)
from agent.subagents.loader import load_subagent_configs
configs = load_subagent_configs()
print(f"✅ 加载 {len(configs)} 个子 Agent 配置")
for c in configs:
    print(f"   - {c['name']}: {c['description'][:40]}...")

print("\n" + "=" * 50)
print("测试 3: 任务规划工具")
print("=" * 50)
from agent.tools.planning_tools import write_todos
import json
result = write_todos.invoke({
    "todos": [
        {"id": "1", "content": "查询供应商数据", "status": "pending"},
        {"id": "2", "content": "分析价格趋势", "status": "in_progress", "depends_on": ["1"]},
        {"id": "3", "content": "生成分析报告", "status": "pending", "depends_on": ["2"]},
    ],
    "merge": False,
    "thread_id": "test"
})
data = json.loads(result)
print(f"✅ 任务规划成功")
print(f"   总计: {data['stats']['total']}, 待执行: {data['stats']['pending']}, 执行中: {data['stats']['in_progress']}")

print("\n" + "=" * 50)
print("测试 4: 配置和数据模型")
print("=" * 50)
from agent.config import llm_config, mongo_config, api_config
from agent.schema import ProcurementContext, UserPreferences
print(f"✅ LLM 模型: {llm_config.model}")
print(f"✅ API 端口: {api_config.port}")
ctx = ProcurementContext(user_id="test", username="测试用户")
print(f"✅ 上下文创建: user_id={ctx.user_id}, username={ctx.username}")

print("\n" + "=" * 50)
print("测试 5: 中间件加载")
print("=" * 50)
from agent.middlewares.context_injection import ContextInjectionMiddleware
from agent.middlewares.memory_update import MemoryUpdateMiddleware
from agent.middlewares.sandbox_health import SandboxHealthMiddleware
from agent.middlewares.sandbox_breaker import SandboxCircuitBreakerMiddleware
from agent.middlewares.skills_sync import SkillsSyncMiddleware
from agent.middlewares.tools_summarization import ToolsSummarizationMiddleware
from agent.middlewares.user_skills_restore import UserSkillsRestoreMiddleware
print("✅ 7 个中间件全部加载成功")

print("\n" + "=" * 50)
print("测试 6: 沙箱后端")
print("=" * 50)
from agent.backends.sandbox_manager import SandboxManager
from agent.backends.sandbox_proxy import SandboxBackendProxy
from agent.backends.custom_opensandbox import CustomOpenSandbox
print("✅ 沙箱后端模块加载成功")

print("\n" + "=" * 50)
print("🎉 所有核心模块测试通过！")
print("=" * 50)
