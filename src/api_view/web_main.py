"""
FastAPI 应用入口（CORS、路由注册）
"""
import os
import sys
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
        "version": "1.0.0",
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
