"""Structured chart generation for reports and the Vue client."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List

from langchain_core.tools import tool

from api_view.web_config import get_db
from agent.tools.file_tools import resolve_virtual_path


@tool
def chart_generator(
    title: str,
    chart_type: str = "bar",
    data: Dict[str, Any] = None,
    user_id: str = "default_user",
    x_name: str = "项目",
    y_name: str = "数值",
) -> str:
    """生成 ECharts 可直接消费的结构化图表，并保存为分析附件。"""
    allowed = {"bar", "line", "pie"}
    if chart_type not in allowed:
        return json.dumps({"code": -1, "message": f"不支持的图表类型，可选: {sorted(allowed)}"}, ensure_ascii=False)
    values = data or {}
    if not isinstance(values, dict):
        return json.dumps({"code": -1, "message": "data 必须是对象"}, ensure_ascii=False)

    chart = {
        "type": chart_type,
        "title": title,
        "x_name": x_name,
        "y_name": y_name,
        "data": values,
        "source": "agent_chart_generator",
    }
    filename = f"chart_{uuid.uuid4().hex[:8]}.json"
    local_path, _ = resolve_virtual_path(f"/analysis/{filename}", user_id)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(chart, ensure_ascii=False, indent=2), encoding="utf-8")
    artifact = get_db().create_artifact({
        "artifact_id": f"artifact_{uuid.uuid4().hex[:10]}",
        "name": filename,
        "path": f"/analysis/{filename}",
        "local_path": str(local_path),
        "kind": "chart",
        "user_id": user_id,
        "created_at": time.time(),
        "download_url": "",
    })
    artifact["download_url"] = f"/api/artifacts/{artifact['artifact_id']}/download"
    # Persist the URL update without exposing the underlying document model.
    get_db().create_artifact(artifact)
    return json.dumps({"code": 0, "chart": chart, "artifact": artifact}, ensure_ascii=False)


def get_chart_tools() -> List[Any]:
    return [chart_generator]
