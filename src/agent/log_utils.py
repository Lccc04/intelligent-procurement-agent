"""
日志工具
"""
import sys
from loguru import logger


def setup_logger(level: str = "INFO"):
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.add(
        "logs/app.log",
        level=level,
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )
    return logger


# 全局 logger 实例
log = setup_logger()
