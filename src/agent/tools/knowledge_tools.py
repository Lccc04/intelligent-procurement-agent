"""Stable RAG extension point for future procurement document search."""
from langchain_core.tools import tool
import json


@tool
def knowledge_search(query: str, user_id: str = "default_user", top_k: int = 5) -> str:
    """采购文档检索接口；配置向量库后在此处替换 provider。"""
    return json.dumps({
        "code": 501,
        "query": query,
        "top_k": top_k,
        "provider": "not_configured",
        "message": "知识库检索接口已预留，当前未配置向量数据库或 Embedding 服务",
        "results": [],
    }, ensure_ascii=False)
