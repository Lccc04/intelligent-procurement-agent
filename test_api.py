"""测试 DeepSeek API 连接"""
import sys
sys.path.insert(0, r"F:\基于Java-ERP系统的智能采购助手——Agent项目\src")

from agent.config import llm_config
print(f"模型: {llm_config.model}")
print(f"API Key: {llm_config.api_key[:10]}...")
print(f"Base URL: {llm_config.base_url}")
print()

# 测试连接
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model=llm_config.model,
    api_key=llm_config.api_key,
    base_url=llm_config.base_url,
    temperature=0.1,
)

print("正在测试 API 连接...")
resp = llm.invoke("你好，请回复连接成功四个字")
print(f"API 测试结果: {resp.content}")
print()
print("✅ DeepSeek API 连接成功！")
