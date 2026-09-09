"""Skill lifecycle tools: download/create, validate, assign and persist."""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, List

from langchain_core.tools import tool

from api_view.web_config import get_db
from agent.tools.file_tools import _user_root


def _valid_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}", name or ""))


def _validate_skill(content: str) -> list[str]:
    errors = []
    if len(content.encode("utf-8")) > 256 * 1024:
        errors.append("技能文件超过 256KB")
    if not content.strip():
        errors.append("技能内容为空")
    if "#" not in content:
        errors.append("技能内容至少需要一个 Markdown 标题")
    return errors


@tool
def assign_skill(
    skill_name: str,
    skill_markdown: str = "",
    user_id: str = "default_user",
    source_url: str = "",
) -> str:
    """执行技能生命周期：下载（可选）→创建→测试→分配→持久化。"""
    if not _valid_name(skill_name):
        return json.dumps({"code": -1, "message": "技能名只能包含字母、数字、下划线和短横线"}, ensure_ascii=False)

    content = skill_markdown
    stages = [{"stage": "download", "status": "skipped" if not source_url else "pending"}]
    if source_url:
        if not source_url.startswith("https://"):
            return json.dumps({"code": -1, "message": "source_url 仅允许 HTTPS"}, ensure_ascii=False)
        try:
            import httpx
            response = httpx.get(source_url, timeout=10, follow_redirects=True)
            response.raise_for_status()
            content = response.text[:256 * 1024]
            stages[0]["status"] = "passed"
        except Exception as exc:
            stages[0].update({"status": "failed", "message": str(exc)})
            return json.dumps({"code": -1, "stages": stages}, ensure_ascii=False)

    stages.append({"stage": "create", "status": "pending"})
    errors = _validate_skill(content)
    if errors:
        stages[-1].update({"status": "failed", "errors": errors})
        return json.dumps({"code": -1, "stages": stages}, ensure_ascii=False)

    skill_dir = _user_root(user_id) / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    stages[-1]["status"] = "passed"

    stages.append({"stage": "test", "status": "passed", "checks": ["markdown_not_empty", "size_limit"]})
    record = {
        "name": skill_name,
        "user_id": user_id,
        "path": str(skill_file),
        "assigned_at": time.time(),
        "source_url": source_url or None,
        "status": "assigned",
    }
    stages.append({"stage": "assign", "status": "passed"})
    get_db().assign_skill(user_id, skill_name, record)
    stages.append({"stage": "persist", "status": "passed", "backend": get_db().backend})
    return json.dumps({"code": 0, "message": "技能已创建、测试、分配并持久化", "skill": record, "stages": stages}, ensure_ascii=False)


@tool
def list_assigned_skills(user_id: str = "default_user") -> str:
    """查看用户已持久化的技能分配。"""
    return json.dumps({"code": 0, "user_id": user_id, "skills": get_db().get_skills(user_id)}, ensure_ascii=False)


def get_skill_tools() -> List[Any]:
    return [assign_skill, list_assigned_skills]
