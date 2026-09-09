@echo off
chcp 65001 >nul
echo ========================================
echo   智能采购助手 - 项目启动脚本
echo   Harness Engineering Agent
echo ========================================
echo.

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)
echo ✅ Python 环境正常
echo.

echo [2/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo ⚠️  依赖未安装，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo ✅ 依赖已安装
)
echo.

echo [3/3] 启动服务...
echo.
echo 🌐 服务地址: http://127.0.0.1:8000
echo 📖 API 文档: http://127.0.0.1:8000/docs
echo 💡 按 Ctrl+C 停止服务
echo.

python -m src.api_view.web_main

pause
