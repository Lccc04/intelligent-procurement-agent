"""Application persistence adapters.

The default backend is a local JSON file so the demo starts without services.
Set ``PERSISTENCE_BACKEND=mongo`` to use MongoDB through the same interface.
"""
from __future__ import annotations

import base64
import copy
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PREFERENCES = {
    "preferred_output": "markdown",
    "preferred_chart_type": "bar",
    "preferred_currency": "CNY",
    "preferred_language": "zh-CN",
    "recent_suppliers": [],
    "recent_queries": [],
}


class PersistentDB:
    """Persistence interface shared by the API, tools and middleware."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {
            "sessions": {},
            "messages": {},
            "preferences": {},
            "tasks": {},
            "skills": {},
            "artifacts": {},
            "approval_events": [],
            "checkpoint_state": None,
        }
        self.backend = "file"

    def _load(self) -> None:
        pass

    def _flush(self) -> None:
        pass

    def _mutate(self, callback):
        with self._lock:
            result = callback()
            self._flush()
            return result

    def create_session(self, thread_id: str, user_id: str, username: str):
        def create():
            self._data["sessions"][thread_id] = {
                "thread_id": thread_id,
                "user_id": user_id,
                "username": username,
                "created_at": time.time(),
                "updated_at": time.time(),
                "interrupted": False,
                "interrupt_data": None,
            }
            self._data["messages"][thread_id] = []

        self._mutate(create)

    def get_session(self, thread_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            value = self._data["sessions"].get(thread_id)
            return copy.deepcopy(value) if value else None

    def update_session(self, thread_id: str, **kwargs):
        def update():
            session = self._data["sessions"].get(thread_id)
            if session:
                session.update(copy.deepcopy(kwargs))
                session["updated_at"] = time.time()

        self._mutate(update)

    def list_sessions(self, user_id: str = None) -> List[Dict[str, Any]]:
        with self._lock:
            result = list(self._data["sessions"].values())
            if user_id:
                result = [item for item in result if item.get("user_id") == user_id]
            result.sort(key=lambda item: item.get("updated_at", 0), reverse=True)
            return copy.deepcopy(result)

    def delete_session(self, thread_id: str):
        def delete():
            self._data["sessions"].pop(thread_id, None)
            self._data["messages"].pop(thread_id, None)

        self._mutate(delete)

    def add_message(self, thread_id: str, role: str, content: str, **kwargs):
        def add():
            self._data["messages"].setdefault(thread_id, []).append({
                "role": role,
                "content": content,
                "timestamp": time.time(),
                **kwargs,
            })
            if thread_id in self._data["sessions"]:
                self._data["sessions"][thread_id]["updated_at"] = time.time()

        self._mutate(add)

    def get_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._data["messages"].get(thread_id, []))

    def save_display_messages(self, thread_id: str, messages: List[Dict[str, Any]]):
        def save():
            self._data["messages"][thread_id] = copy.deepcopy(messages)
            if thread_id in self._data["sessions"]:
                self._data["sessions"][thread_id]["updated_at"] = time.time()

        self._mutate(save)

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        with self._lock:
            result = copy.deepcopy(DEFAULT_PREFERENCES)
            result.update(copy.deepcopy(self._data["preferences"].get(user_id, {})))
            return result

    def update_preferences(self, user_id: str, prefs: Dict[str, Any]):
        def update():
            current = self.get_preferences(user_id)
            current.update(copy.deepcopy(prefs))
            self._data["preferences"][user_id] = current

        self._mutate(update)

    def create_task(self, task: Dict[str, Any]):
        self._mutate(lambda: self._data["tasks"].__setitem__(task["task_id"], copy.deepcopy(task)))

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            value = self._data["tasks"].get(task_id)
            return copy.deepcopy(value) if value else None

    def update_task(self, task_id: str, **updates):
        def update():
            task = self._data["tasks"].get(task_id)
            if task:
                task.update(copy.deepcopy(updates))
                task["updated_at"] = time.time()

        self._mutate(update)

    def list_tasks(self, user_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            tasks = list(self._data["tasks"].values())
            if user_id:
                tasks = [task for task in tasks if task.get("user_id") == user_id]
            tasks.sort(key=lambda item: item.get("created_at", 0), reverse=True)
            return copy.deepcopy(tasks[:limit])

    def assign_skill(self, user_id: str, skill_name: str, record: Dict[str, Any]):
        def assign():
            self._data["skills"].setdefault(user_id, {})[skill_name] = copy.deepcopy(record)

        self._mutate(assign)

    def get_skills(self, user_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(list(self._data["skills"].get(user_id, {}).values()))

    def create_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        self._mutate(lambda: self._data["artifacts"].__setitem__(
            artifact["artifact_id"], copy.deepcopy(artifact)
        ))
        return copy.deepcopy(artifact)

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            value = self._data["artifacts"].get(artifact_id)
            return copy.deepcopy(value) if value else None

    def list_artifacts(self, user_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._data["artifacts"].values())
            if user_id:
                items = [item for item in items if item.get("user_id") == user_id]
            items.sort(key=lambda item: item.get("created_at", 0), reverse=True)
            return copy.deepcopy(items[:limit])

    def save_checkpoint_blob(self, value: bytes):
        encoded = base64.b64encode(value).decode("ascii")
        self._mutate(lambda: self._data.__setitem__("checkpoint_state", encoded))

    def load_checkpoint_blob(self) -> Optional[bytes]:
        with self._lock:
            value = self._data.get("checkpoint_state")
            return base64.b64decode(value) if value else None

    # ===== human approval audit and statistics =====
    def record_approval_trigger(
        self,
        thread_id: str,
        user_id: str,
        interrupt_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create one pending approval event when an HITL interrupt fires."""
        action_requests = interrupt_data.get("action_requests") or []
        first_action = action_requests[0] if action_requests else {}
        record = {
            "approval_id": f"approval_{uuid.uuid4().hex[:12]}",
            "thread_id": thread_id,
            "user_id": user_id,
            "action": first_action.get("name", "unknown"),
            "description": first_action.get("description", ""),
            "status": "pending",
            "triggered_at": time.time(),
            "resolved_at": None,
            "response_seconds": None,
        }

        def add():
            events = self._data.setdefault("approval_events", [])
            events.append(record)
            # Keep the audit ledger bounded for the local demo store.
            del events[:-2000]

        self._mutate(add)
        return copy.deepcopy(record)

    def record_approval_resolution(
        self,
        approval_id: str,
        status: str,
        thread_id: str = "",
        user_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Resolve a pending approval exactly once."""
        allowed = {"approved", "rejected", "cancelled"}
        resolved_status = status if status in allowed else "cancelled"
        resolved = None

        def update():
            nonlocal resolved
            for event in self._data.setdefault("approval_events", []):
                if event.get("approval_id") != approval_id or event.get("status") != "pending":
                    continue
                now = time.time()
                event.update({
                    "status": resolved_status,
                    "resolved_at": now,
                    "response_seconds": round(max(0, now - event.get("triggered_at", now)), 3),
                })
                if thread_id:
                    event["thread_id"] = thread_id
                if user_id:
                    event["user_id"] = user_id
                resolved = copy.deepcopy(event)
                break

        self._mutate(update)
        return resolved

    def get_approval_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Calculate approval KPIs from the durable audit ledger."""
        with self._lock:
            events = list(self._data.get("approval_events", []))
            if user_id:
                events = [event for event in events if event.get("user_id") == user_id]
            total = len(events)
            approved = sum(event.get("status") == "approved" for event in events)
            rejected = sum(event.get("status") == "rejected" for event in events)
            cancelled = sum(event.get("status") == "cancelled" for event in events)
            pending = sum(event.get("status") == "pending" for event in events)
            resolved = approved + rejected + cancelled
            response_times = [
                event["response_seconds"] for event in events
                if isinstance(event.get("response_seconds"), (int, float))
            ]
            by_action: Dict[str, int] = {}
            for event in events:
                action = event.get("action", "unknown")
                by_action[action] = by_action.get(action, 0) + 1
            recent = sorted(events, key=lambda event: event.get("triggered_at", 0), reverse=True)[:20]
            return {
                "total": total,
                "pending": pending,
                "approved": approved,
                "rejected": rejected,
                "cancelled": cancelled,
                "resolved": resolved,
                "response_rate": round(resolved / total * 100, 1) if total else 0,
                "avg_response_seconds": round(sum(response_times) / len(response_times), 2) if response_times else None,
                "by_action": by_action,
                "recent_events": copy.deepcopy(recent),
            }


class FileDB(PersistentDB):
    """Durable local fallback for development and demonstrations."""

    def __init__(self, path: str):
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                self._data.update(loaded)
        except (OSError, ValueError) as exc:
            print(f"持久化文件读取失败，将使用空存储: {exc}")

    def _flush(self):
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False)
        temp_path.replace(self.path)


class MongoDB(PersistentDB):
    """MongoDB implementation using one application state document."""

    def __init__(self, url: str, database_name: str):
        super().__init__()
        from pymongo import MongoClient

        self.client = MongoClient(url, serverSelectionTimeoutMS=1200)
        self.client.admin.command("ping")
        self.collection = self.client[database_name]["application_state"]
        self.backend = "mongo"
        self._load()

    def _load(self):
        document = self.collection.find_one({"_id": "singleton"})
        if document:
            document.pop("_id", None)
            self._data.update(document)

    def _flush(self):
        self.collection.replace_one({"_id": "singleton"}, {"_id": "singleton", **self._data}, upsert=True)


def build_db() -> PersistentDB:
    if os.getenv("PERSISTENCE_BACKEND", "file").lower() == "mongo":
        try:
            from agent.config import mongo_config
            store = MongoDB(mongo_config.url, mongo_config.db_name)
            print("✅ MongoDB 持久化已启用")
            return store
        except Exception as exc:
            print(f"⚠️ MongoDB 不可用，回退到本地持久化: {exc}")

    project_root = Path(__file__).resolve().parents[2]
    path = os.getenv("PERSISTENCE_FILE", str(project_root / ".agent_runtime" / "store.json"))
    return FileDB(path)
