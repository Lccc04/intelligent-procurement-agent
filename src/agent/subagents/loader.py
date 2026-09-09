"""
子 Agent 配置加载器
YAML 加载 + 工具名解析
"""
import os
import hashlib
import yaml
from typing import List, Dict, Any
from agent.log_utils import log


# 子 Agent 配置目录
CONFIGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")


def load_subagent_configs() -> List[Dict[str, Any]]:
    """
    加载所有子 Agent 配置文件
    读取 configs/*.yaml，校验必填字段，返回原始 dict 列表
    """
    configs = []
    if not os.path.exists(CONFIGS_DIR):
        log.warning(f"子 Agent 配置目录不存在: {CONFIGS_DIR}")
        return configs

    for filename in sorted(os.listdir(CONFIGS_DIR)):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(CONFIGS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                if _validate_subagent_config(config):
                    configs.append(config)
                    log.info(f"✅ 加载子 Agent 配置: {config.get('name')} ({filename})")
            except Exception as e:
                log.error(f"加载子 Agent 配置失败 {filename}: {e}")

    return configs


def resolve_subagent_tools(
    config: Dict[str, Any],
    available_tools: list
) -> List[Any]:
    """
    将 tools 字符串通过子串匹配映射为实际工具对象

    Args:
        config: 子 Agent 配置 dict
        available_tools: 所有可用工具列表（LangChain Tool 对象）

    Returns:
        匹配到的工具列表
    """
    tool_names = config.get("tools", [])
    resolved = []

    for tool_name in tool_names:
        # Prefer exact names.  The previous substring match could silently
        # bind a similarly named tool after a YAML file was added.
        exact = next((tool for tool in available_tools if getattr(tool, "name", None) == tool_name), None)
        if exact is not None:
            resolved.append(exact)
            continue
        for tool in available_tools:
            if hasattr(tool, "name") and tool_name.lower() == tool.name.lower():
                resolved.append(tool)
                break
        else:
            log.warning(f"⚠️ 子 Agent {config.get('name')} 未找到工具: {tool_name}")

    return resolved


def _validate_subagent_config(config: Dict[str, Any]) -> bool:
    """校验子 Agent 配置的必填字段"""
    required_fields = ["name", "description", "system_prompt", "tools"]
    for field in required_fields:
        if field not in config:
            log.error(f"子 Agent 配置缺少必填字段: {field}")
            return False
    return True


def get_subagent_by_name(name: str) -> Dict[str, Any]:
    """按名称获取子 Agent 配置"""
    configs = load_subagent_configs()
    for config in configs:
        if config.get("name") == name:
            return config
    return None


def get_config_signature() -> str:
    """Return a digest so long-lived processes can hot-reload YAML configs."""
    digest = hashlib.sha256()
    if not os.path.exists(CONFIGS_DIR):
        return ""
    for filename in sorted(os.listdir(CONFIGS_DIR)):
        if filename.endswith((".yaml", ".yml")):
            path = os.path.join(CONFIGS_DIR, filename)
            digest.update(filename.encode("utf-8"))
            with open(path, "rb") as handle:
                digest.update(handle.read())
    return digest.hexdigest()
