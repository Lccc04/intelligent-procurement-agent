"""
FastAPI 应用入口（CORS、路由注册）
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 确保 src 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api_view.agent_loader import get_agent_loader
from api_view.api.chat import router as chat_router
from api_view.api.history import router as history_router
from agent.config import api_config
from agent.log_utils import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 Agent"""
    log.info("🚀 应用启动中...")
    # 预初始化 Agent
    loader = get_agent_loader()
    loader.initialize()
    from agent.tools.async_tools import recover_pending_tasks
    recover_pending_tasks()
    log.info("✅ 应用启动完成")
    yield
    log.info("👋 应用关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title="智能采购助手 - Harness Engineering Agent",
    description="基于 Harness Engineering 架构的企业级智能采购 Agent 系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(history_router)


# 健康检查
@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    loader = get_agent_loader()
    return {
        "code": 0,
        "status": "ok",
        "agent_initialized": loader.agent is not None,
        "version": "1.1.0",
        "persistence_backend": loader.db.backend,
    }


# 前端页面（如果存在）
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        """服务前端页面"""
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "前端页面未找到"}


@app.get("/api/tasks")
async def list_tasks(user_id: str = None, limit: int = 50):
    """任务列表，供 Vue 轮询和恢复展示。"""
    from agent.tools.async_tools import get_all_async_tasks
    tasks = list(get_all_async_tasks().values())
    if user_id:
        tasks = [task for task in tasks if task.get("user_id") == user_id]
    tasks.sort(key=lambda item: item.get("created_at", 0), reverse=True)
    return {"code": 0, "data": tasks[:max(1, min(limit, 200))], "total": len(tasks)}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    from agent.tools.async_tools import check_async_task
    import json
    return json.loads(check_async_task.invoke({"task_id": task_id}))


@app.get("/api/approvals/stats")
async def approval_stats(user_id: str = None):
    """人工审批触发、处理结果和响应时长统计。"""
    return {"code": 0, "data": get_agent_loader().db.get_approval_stats(user_id)}


@app.get("/api/artifacts")
async def list_artifacts(user_id: str = None):
    artifacts = get_agent_loader().db.list_artifacts(user_id)
    return {"code": 0, "data": artifacts, "total": len(artifacts)}


@app.get("/api/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    from fastapi import HTTPException
    artifact = get_agent_loader().db.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = Path(artifact.get("local_path", "")).resolve()
    allowed_roots = [Path(frontend_dir).resolve().parent / ".agent_runtime", Path(frontend_dir).resolve().parent / "src" / "skills"]
    if not any(path == root or root in path.parents for root in allowed_roots) or not path.is_file():
        raise HTTPException(status_code=404, detail="附件文件不可用")
    return FileResponse(path, filename=artifact.get("name", path.name))


@app.get("/api/subagents")
async def list_subagents():
    from agent.tools.subagent_tools import get_subagent_catalog
    data = get_subagent_catalog()
    return {"code": 0, "data": data, "total": len(data)}


@app.get("/api/erps")
async def list_erps():
    from agent.tools.mock_tools import get_erp_catalog
    data = get_erp_catalog()
    return {"code": 0, "data": data, "total": len(data)}


def main():
    """启动应用"""
    import uvicorn
    log.info(f"🌐 服务启动: http://{api_config.host}:{api_config.port}")
    log.info(f"📖 API 文档: http://{api_config.host}:{api_config.port}/docs")
    uvicorn.run(
        "src.api_view.web_main:app",
        host=api_config.host,
        port=api_config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
