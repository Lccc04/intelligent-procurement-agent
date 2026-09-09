"""Single source of truth for tools available to dynamically loaded agents."""
from typing import Any, List

from agent.tools.mock_tools import get_all_mock_tools
from agent.tools.file_tools import get_file_tools
from agent.tools.chart_tools import get_chart_tools
from agent.tools.skill_tools import get_skill_tools
from agent.tools.knowledge_tools import knowledge_search
from agent.tools.hitl_tools import request_order_info


def get_all_runtime_tools() -> List[Any]:
    tools = [
        *get_all_mock_tools(),
        *get_file_tools(),
        *get_chart_tools(),
        *get_skill_tools(),
        knowledge_search,
        request_order_info,
    ]
    unique = {}
    for item in tools:
        unique[item.name] = item
    return list(unique.values())
