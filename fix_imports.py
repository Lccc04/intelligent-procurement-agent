"""批量修复相对导入为绝对导入"""
import os
import re

BASE_DIR = r"C:\Users\不必有所回应\Doubao\chats\2026-09-09\new-chat-1\procurement-agent\src"

def fix_imports(filepath):
    """修复单个文件的导入"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    rel_path = os.path.relpath(filepath, BASE_DIR).replace("\\", "/")
    parts = rel_path.split("/")

    # 根据文件位置确定模块前缀
    if parts[0] == "agent":
        if len(parts) >= 3 and parts[1] in ["tools", "middlewares", "backends", "subagents", "memory"]:
            # agent/subdir/file.py
            # from ..xxx -> from agent.xxx
            # from .xxx -> from agent.subdir.xxx
            content = re.sub(r'from \.\.(\w+)', r'from agent.\1', content)
            content = re.sub(r'from \.(\w+)', f'from agent.{parts[1]}.\\1', content)
        else:
            # agent/file.py
            # from .xxx -> from agent.xxx
            content = re.sub(r'from \.(\w+)', r'from agent.\1', content)

    elif parts[0] == "api_view":
        if len(parts) >= 3 and parts[1] == "api":
            # api_view/api/file.py
            # from ...agent.xxx -> from agent.xxx
            # from ..xxx -> from api_view.xxx
            content = re.sub(r'from \.\.\.agent\.(\w+)', r'from agent.\1', content)
            content = re.sub(r'from \.\.(\w+)', r'from api_view.\1', content)
        else:
            # api_view/file.py
            # from ..agent.xxx -> from agent.xxx
            # from .xxx -> from api_view.xxx
            content = re.sub(r'from \.\.agent\.(\w+)', r'from agent.\1', content)
            content = re.sub(r'from \.(\w+)', r'from api_view.\1', content)

    elif parts[0] == "mcp_server":
        if len(parts) >= 3 and parts[1] == "tools":
            # mcp_server/tools/file.py
            # from ..xxx -> from mcp_server.xxx
            content = re.sub(r'from \.\.(\w+)', r'from mcp_server.\1', content)
        else:
            # mcp_server/file.py
            # from .xxx -> from mcp_server.xxx
            content = re.sub(r'from \.(\w+)', r'from mcp_server.\1', content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 修复: {rel_path}")
        return True
    return False


def main():
    count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                if fix_imports(filepath):
                    count += 1
    print(f"\n🎉 共修复 {count} 个文件")


if __name__ == "__main__":
    main()
