"""Durable LangGraph checkpoint adapter.

LangGraph's in-memory saver is still used for its well-tested checkpoint
semantics.  Its storage is snapshotted to the application store after writes,
which keeps interrupt/resume state available after a process restart.
"""
from __future__ import annotations

import pickle
import threading
from collections import defaultdict
from typing import Any, Sequence

from langgraph.checkpoint.memory import InMemorySaver


def _to_plain_dict(value):
    """Remove defaultdict factories before serializing LangGraph state."""
    if isinstance(value, dict):
        return {key: _to_plain_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_dict(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_to_plain_dict(item) for item in value)
    return value


class PersistentCheckpointSaver(InMemorySaver):
    """InMemorySaver with a durable application-store snapshot."""

    def __init__(self, store):
        super().__init__()
        self.store = store
        self._persist_lock = threading.RLock()
        self._restore()

    def _restore(self):
        try:
            blob = self.store.load_checkpoint_blob()
            if not blob:
                return
            state = pickle.loads(blob)
            if isinstance(state, dict):
                if "storage" in state:
                    self.storage = defaultdict(lambda: defaultdict(dict))
                    for thread_id, namespaces in state["storage"].items():
                        self.storage[thread_id] = defaultdict(dict, namespaces)
                if "writes" in state:
                    self.writes = defaultdict(dict, state["writes"])
                if "blobs" in state:
                    self.blobs = state["blobs"]
        except Exception:
            self.storage.clear()
            self.writes.clear()
            self.blobs.clear()

    def _persist(self):
        with self._persist_lock:
            snapshot = pickle.dumps({
                "storage": _to_plain_dict(self.storage),
                "writes": _to_plain_dict(self.writes),
                "blobs": _to_plain_dict(self.blobs),
            })
            self.store.save_checkpoint_blob(snapshot)

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        self._persist()
        return result

    def put_writes(self, config, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = ""):
        result = super().put_writes(config, writes, task_id, task_path)
        self._persist()
        return result

    def delete_thread(self, thread_id: str):
        result = super().delete_thread(thread_id)
        self._persist()
        return result
