#!/usr/bin/env python3
"""
シンプルなエージェントテスト
"""

import os
from src.edinet_analyzer import create_agent

# テスト用の環境変数設定
os.environ["OPENAI_API_KEY"] = "test_key_for_demo"
os.environ["EDINET_API_KEY"] = "test_key_for_demo"

print("エージェントを作成中...")
agent = create_agent(enable_memory=False)

print("環境検証中...")
validation = agent.validate_environment()
for key, value in validation.items():
    print(f"{key}: {value}")

print("\nワークフロー図:")
print(agent.get_workflow_diagram())

print("\n質問テスト:")
result = agent.invoke("楽天グループの総資産を教えてください")
print(f"企業名: {result.get('company_name')}")
print(f"エラー: {result.get('error_message')}")
print(f"回答: {result.get('final_answer', '')[:200]}...")