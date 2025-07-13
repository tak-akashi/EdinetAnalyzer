#!/usr/bin/env python3
"""
実際のAPIキーを使ったテスト
.envファイルからAPIキーを読み込みます
"""

import os
from dotenv import load_dotenv
from src.edinet_analyzer import create_agent

# .envファイルを読み込み
load_dotenv()

def test_with_real_keys():
    # APIキーの確認
    openai_key = os.environ.get("OPENAI_API_KEY")
    edinet_key = os.environ.get("EDINET_API_KEY")
    
    if not openai_key or openai_key.startswith("test"):
        print("❌ 実際のOPENAI_API_KEYを環境変数に設定してください")
        print("export OPENAI_API_KEY='your_actual_key'")
        return False
    
    if not edinet_key or edinet_key.startswith("test"):
        print("❌ 実際のEDINET_API_KEYを環境変数に設定してください")
        print("export EDINET_API_KEY='your_actual_key'")
        return False
    
    print("✅ APIキーが設定されています")
    print(f"OpenAI: {openai_key[:10]}...")
    print(f"EDINET: {edinet_key[:10]}...")
    
    try:
        print("\n🤖 エージェントを作成中...")
        agent = create_agent(enable_memory=False)
        
        print("📋 環境検証中...")
        validation = agent.validate_environment()
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}")
        
        if not all(validation.values()):
            print("⚠️  一部の環境設定に問題があります")
        
        print("\n💬 質問テスト:")
        test_query = "楽天グループの総資産を教えてください"
        print(f"質問: {test_query}")
        
        result = agent.invoke(test_query)
        
        print(f"\n📊 結果:")
        print(f"企業名: {result.get('company_name', 'N/A')}")
        print(f"実行時間: {result.get('execution_time', 0):.2f}秒")
        print(f"次のアクション: {result.get('next_action', 'N/A')}")
        
        if result.get('error_message'):
            print(f"⚠️  エラー: {result['error_message']}")
        
        if result.get('final_answer'):
            print(f"\n🤖 回答:\n{result['final_answer']}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return False

if __name__ == "__main__":
    test_with_real_keys()