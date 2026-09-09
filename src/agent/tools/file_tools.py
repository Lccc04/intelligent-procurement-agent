"""Main-agent file and sandbox tools.

Virtual paths intentionally mirror the architecture described in the design
document: ``/skills`` is the read-only built-in library, while ``/workspace``,
``/analysis`` and ``/memories`` are user-scoped writable areas.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.tools import tool

from api_view.web_config import get_db


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / ".agent_runtime"
BUILTIN_SKILLS_ROOT = PROJECT_ROOT / "src" / "skills"
MAX_FILE_SIZE = 2 * 1024 * 1024


def _user_root(user_id: str) -> Path:
    safe_user = "".join(char for char in (user_id or "default_user") if char.isalnum() or char in "-_")
    return RUNTIME_ROOT / "users" / (safe_user or "default_user")


def resolve_virtual_path(path: str, user_id: str = "default_user") -> tuple[Path, bool]:
    """Resolve a virtual path and return ``(local_path, read_only)``."""
    raw = (path or ".").replace("\\", "/")
    if raw.startswith("/skills"):
        relative = raw[len("/skills"):].lstrip("/")
        root, read_only = BUILTIN_SKILLS_ROOT, True
    elif raw.startswith("/analysis"):
        relative = raw[len("/analysis"):].lstrip("/")
        root, read_only = _user_root(user_id) / "analysis", False
    elif raw.startswith("/memories"):
        relative = raw[len("/memories"):].lstrip("/")
        root, read_only = _user_root(user_id) / "memories", False
    elif raw.startswith("/workspace"):
        relative = raw[len("/workspace"):].lstrip("/")
        root, read_only = _user_root(user_id) / "workspace", False
    else:
        relative = raw.lstrip("/")
        root, read_only = _user_root(user_id) / "workspace", False

    root = root.resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError("文件路径超出允许的工作区范围")
    return target, read_only


def _file_record(path: Path, virtual_path: str) -> Dict[str, Any]:
    stat = path.stat()
    return {
        "path": virtual_path,
        "name": path.name,
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size if path.is_file() else None,
        "modified_at": stat.st_mtime,
    }


def _artifact_for_file(path: Path, virtual_path: str, user_id: str, kind: str = "file") -> Dict[str, Any]:
    artifact = {
        "artifact_id": f"artifact_{uuid.uuid4().hex[:10]}",
        "name": path.name,
        "path": virtual_path,
        "local_path": str(path),
        "kind": kind,
        "user_id": user_id,
        "created_at": __import__("time").time(),
        "download_url": f"/api/artifacts/{{artifact_id}}/download",
    }
    artifact["download_url"] = artifact["download_url"].format(artifact_id=artifact["artifact_id"])
    return get_db().create_artifact(artifact)


@tool
def list_files(path: str = "/skills", user_id: str = "default_user") -> str:
    """渐进式列出虚拟目录，只返回文件名、类型和大小，不一次性塞入全部内容。"""
    try:
        local_path, _ = resolve_virtual_path(path, user_id)
        if not local_path.exists():
            return json.dumps({"code": -1, "message": "目录不存在", "path": path}, ensure_ascii=False)
        if not local_path.is_dir():
            return json.dumps({"code": -1, "message": "目标不是目录", "path": path}, ensure_ascii=False)
        entries = []
        for child in sorted(local_path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))[:200]:
            child_virtual = f"{path.rstrip('/')}/{child.name}" if path != "/" else f"/{child.name}"
            entries.append(_file_record(child, child_virtual))
        return json.dumps({"code": 0, "path": path, "entries": entries, "progressive_disclosure": True}, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"code": -1, "message": str(exc)}, ensure_ascii=False)


@tool
def read_file(path: str, user_id: str = "default_user", offset: int = 0, limit: int = 12000) -> str:
    """读取文件片段；通过 offset/limit 支持技能手册和报告的渐进式披露。"""
    try:
        local_path, _ = resolve_virtual_path(path, user_id)
        if not local_path.exists() or not local_path.is_file():
            return json.dumps({"code": -1, "message": "文件不存在", "path": path}, ensure_ascii=False)
        if local_path.stat().st_size > MAX_FILE_SIZE:
            return json.dumps({"code": -1, "message": "文件超过读取大小限制", "path": path}, ensure_ascii=False)
        content = local_path.read_text(encoding="utf-8")
        start = max(0, offset)
        end = start + max(1, min(limit, MAX_FILE_SIZE))
        return json.dumps({
            "code": 0,
            "path": path,
            "content": content[start:end],
            "offset": start,
            "next_offset": end if end < len(content) else None,
            "truncated": end < len(content),
            "source": "builtin_skills" if path.startswith("/skills") else "user_workspace",
        }, ensure_ascii=False)
    except (OSError, UnicodeError, ValueError) as exc:
        return json.dumps({"code": -1, "message": str(exc)}, ensure_ascii=False)


@tool
def write_file(path: str, content: str, user_id: str = "default_user") -> str:
    """在用户工作区创建或覆盖文本文件。内置技能目录保持只读。"""
    try:
        local_path, read_only = resolve_virtual_path(path, user_id)
        if read_only:
            return json.dumps({"code": -1, "message": "内置技能目录只读，请使用 assign_skill 分配新技能"}, ensure_ascii=False)
        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return json.dumps({"code": -1, "message": "文件超过大小限制"}, ensure_ascii=False)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8")
        artifact = _artifact_for_file(local_path, path, user_id)
        return json.dumps({"code": 0, "message": "文件已写入", "artifact": artifact}, ensure_ascii=False)
    except (OSError, UnicodeError, ValueError) as exc:
        return json.dumps({"code": -1, "message": str(exc)}, ensure_ascii=False)


@tool
def create_file(path: str, content: str = "", user_id: str = "default_user") -> str:
    """显式创建工作区文件，接口语义与 write_file 相同但用于报告/技能工作流。"""
    return write_file.invoke({"path": path, "content": content, "user_id": user_id})


@tool
def execute_code(code: str, user_id: str = "default_user", timeout: int = 15) -> str:
    """在 Docker 沙箱中执行 Python；Docker 不可用时返回明确错误，不回退到宿主机执行。"""
    if os.getenv("SANDBOX_ENABLED", "false").lower() != "true":
        return json.dumps({"code": -2, "message": "Docker 沙箱未启用，请设置 SANDBOX_ENABLED=true"}, ensure_ascii=False)
    try:
        from agent.backends.sandbox_proxy import get_sandbox_proxy
        proxy = get_sandbox_proxy()
        manager = getattr(proxy, "_backend", None)
        if manager and hasattr(manager, "manager") and not manager.manager.health_check():
            manager.manager.create(user_id)
        result = __import__("asyncio").run(proxy.execute(code, min(max(timeout, 1), 60)))
        return json.dumps({"code": result.get("code", -1), "output": result.get("output", ""), "error": result.get("error")}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"code": -1, "message": f"沙箱执行失败: {exc}"}, ensure_ascii=False)


@tool
def test_file(path: str, user_id: str = "default_user", run: bool = False) -> str:
    """测试 Python 文件：默认做语法检查，run=true 时交给 Docker 沙箱执行。"""
    try:
        local_path, _ = resolve_virtual_path(path, user_id)
        source = local_path.read_text(encoding="utf-8")
        compile(source, str(local_path), "exec")
        if not run:
            return json.dumps({"code": 0, "status": "passed", "mode": "syntax", "path": path}, ensure_ascii=False)
        return execute_code.invoke({"code": source, "user_id": user_id})
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        return json.dumps({"code": -1, "status": "failed", "path": path, "message": str(exc)}, ensure_ascii=False)


@tool
def download_sandbox_file(path: str, user_id: str = "default_user") -> str:
    """登记沙箱/工作区文件为可下载附件，返回前端可直接使用的下载地址。"""
    try:
        local_path, _ = resolve_virtual_path(path, user_id)
        if not local_path.exists() or not local_path.is_file():
            return json.dumps({"code": -1, "message": "文件不存在", "path": path}, ensure_ascii=False)
        artifact = _artifact_for_file(local_path, path, user_id, kind="sandbox_file")
        return json.dumps({"code": 0, "artifact": artifact}, ensure_ascii=False)
    except (OSError, ValueError) as exc:
        return json.dumps({"code": -1, "message": str(exc)}, ensure_ascii=False)


def get_file_tools() -> List[Any]:
    return [list_files, read_file, write_file, create_file, execute_code, test_file, download_sandbox_file]
