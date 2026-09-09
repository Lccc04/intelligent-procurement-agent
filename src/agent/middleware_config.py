"""Middleware stack wired into the LangGraph pre/post model hooks."""
from __future__ import annotations

from typing import Any, Dict, Iterable

from agent.middlewares.context_injection import ContextInjectionMiddleware
from agent.middlewares.memory_update import MemoryUpdateMiddleware
from agent.middlewares.sandbox_breaker import SandboxCircuitBreakerMiddleware
from agent.middlewares.sandbox_health import SandboxHealthMiddleware
from agent.middlewares.skills_sync import SkillsSyncMiddleware
from agent.middlewares.tools_summarization import ToolsSummarizationMiddleware
from agent.middlewares.user_skills_restore import UserSkillsRestoreMiddleware


class AgentMiddlewareStack:
    """Runs the existing middleware contracts at every LangGraph model turn."""

    def __init__(self, db, user_context=None):
        self.middlewares = [
            SandboxHealthMiddleware(),
            SandboxCircuitBreakerMiddleware(),
            ContextInjectionMiddleware(user_context=user_context),
            SkillsSyncMiddleware(),
            UserSkillsRestoreMiddleware(db=db),
            ToolsSummarizationMiddleware(),
            MemoryUpdateMiddleware(db=db),
        ]

    def before_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        working = dict(state)
        for middleware in self.middlewares:
            method = getattr(middleware, "before_agent", None)
            if method:
                working = method(working) or working
        # llm_input_messages avoids changing LangGraph's message reducer while
        # still allowing summarization and guard middleware to affect context.
        return {"llm_input_messages": working.get("messages", state.get("messages", []))}

    def after_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        working = dict(state)
        for middleware in reversed(self.middlewares):
            method = getattr(middleware, "after_agent", None)
            if method:
                working = method(working) or working
        return {}
