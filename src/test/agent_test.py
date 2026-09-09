"""
Agent 集成测试
测试主 Agent 是否能正常初始化和响应
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agent.main_agent import create_main_agent, precompute_agent_context
from agent.log_utils import log


async def test_agent_init():
    """测试 Agent 初始化"""
    print("=" * 50)
    print("测试 1: Agent 初始化")
    print("=" * 50)

    try:
        context = precompute_agent_context(
            user_id="test_user",
            username="测试用户"
        )
        print(f"✅ 上下文预计算成功: user_id={context.user_id}")

        agent = create_main_agent(context)
        print(f"✅ 主 Agent 创建成功")
        return True
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tools_loaded():
    """测试工具是否加载"""
    print("\n" + "=" * 50)
    print("测试 2: 工具加载")
    print("=" * 50)

    try:
        from agent.tools.mock_tools import get_all_mock_tools
        tools = get_all_mock_tools()
        print(f"✅ Mock 工具加载成功: {len(tools)} 个")
        for t in tools:
            print(f"   - {t.name}")
        return True
    except Exception as e:
        print(f"❌ 工具加载失败: {e}")
        return False


async def test_subagent_config():
    """测试子 Agent 配置加载"""
    print("\n" + "=" * 50)
    print("测试 3: 子 Agent 配置加载")
    print("=" * 50)

    try:
        from agent.subagents.loader import load_subagent_configs
        configs = load_subagent_configs()
        print(f"✅ 子 Agent 配置加载成功: {len(configs)} 个")
        for c in configs:
            print(f"   - {c.get('name')}: {c.get('description', '')[:50]}...")
        return True
    except Exception as e:
        print(f"❌ 子 Agent 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_planning_tool():
    """测试任务规划工具"""
    print("\n" + "=" * 50)
    print("测试 4: 任务规划工具")
    print("=" * 50)

    try:
        from agent.tools.planning_tools import write_todos
        import json

        result = write_todos.invoke({
            "todos": [
                {"id": "1", "content": "查询供应商数据", "status": "pending"},
                {"id": "2", "content": "分析价格趋势", "status": "pending", "depends_on": ["1"]},
                {"id": "3", "content": "生成分析报告", "status": "pending", "depends_on": ["2"]},
            ],
            "merge": False,
            "thread_id": "test_thread"
        })

        data = json.loads(result)
        print(f"✅ 任务规划工具调用成功")
        print(f"   任务数: {data['stats']['total']}")
        print(f"   待执行: {data['stats']['pending']}")
        return True
    except Exception as e:
        print(f"❌ 任务规划工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_task():
    """测试异步任务工具"""
    print("\n" + "=" * 50)
    print("测试 5: 异步任务工具")
    print("=" * 50)

    try:
        from agent.tools.async_tools import start_async_task, check_async_task
        import json

        result = start_async_task.invoke({
            "task_type": "procurement_analysis",
            "instruction": "分析刹车片价格趋势",
            "user_id": "test_user"
        })
        data = json.loads(result)
        task_id = data.get("task_id")
        print(f"✅ 异步任务启动成功: task_id={task_id}")

        # 等待一下再查询
        await asyncio.sleep(1)
        status_result = check_async_task.invoke({"task_id": task_id})
        status_data = json.loads(status_result)
        print(f"✅ 异步任务状态查询: status={status_data.get('status')}")
        return True
    except Exception as e:
        print(f"❌ 异步任务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "🚀 开始运行 Agent 集成测试\n")

    results = []
    results.append(await test_agent_init())
    results.append(await test_tools_loaded())
    results.append(await test_subagent_config())
    results.append(await test_planning_tool())
    results.append(await test_async_task())

    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  {total - passed} 个测试失败")

    return passed == total


if __name__ == "__main__":
    asyncio.run(main())
