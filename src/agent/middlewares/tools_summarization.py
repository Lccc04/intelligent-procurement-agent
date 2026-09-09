"""
工具摘要中间件
compact_conversation 工具，用于上下文压缩
"""
from typing import Dict, Any, List
from agent.log_utils import log


class ToolsSummarizationMiddleware:
    """工具摘要 / 对话压缩中间件"""

    def __init__(self, max_messages: int = 20, compression_threshold: int = 15):
        self.max_messages = max_messages
        self.compression_threshold = compression_threshold

    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行前检查是否需要压缩"""
        messages = state.get("messages", [])
        if len(messages) > self.compression_threshold:
            log.info(f"📝 消息数 {len(messages)} 超过阈值 {self.compression_threshold}，触发压缩")
            state["messages"] = self._compress_messages(messages)
        return state

    def _compress_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩消息（简化版：保留最近 N 条，前面的合并为摘要）"""
        if len(messages) <= self.max_messages:
            return messages

        # 保留最近的消息
        recent = messages[-self.max_messages:]

        # 前面的消息生成摘要（实际项目中用 LLM 摘要）
        old_messages = messages[:-self.max_messages]
        summary = {
            "role": "system",
            "content": f"[对话摘要] 此前有 {len(old_messages)} 条消息，包含用户的历史查询和 Agent 的回复。"
        }

        return [summary] + recent
