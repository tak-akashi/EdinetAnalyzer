#!/usr/bin/env python3
"""
EDINET分析エージェントの手動テストスクリプト
"""

import os
from src.edinet_analyzer import create_agent

def test_agent():
    """エージェントの機能テスト"""
    
    # 環境変数の設定（必要に応じて実際のAPIキーに変更）
    os.environ["OPENAI_API_KEY"] = "test_key_for_demo"  # 実際のキーに変更してください
    os.environ["EDINET_API_KEY"] = "test_key_for_demo"   # 実際のキーに変更してください
    
    print("=" * 60)
    print("EDINET分析エージェント 機能テスト")
    print("=" * 60)
    
    try:
        # エージェントの作成
        print("1. エージェントを作成中...")
        agent = create_agent(enable_memory=False)
        print("✅ エージェントの作成が完了しました")
        
        # 環境検証
        print("\n2. 環境を検証中...")
        validation = agent.validate_environment()
        print("環境検証結果:")
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value}")
        
        # ワークフロー図の表示
        print("\n3. ワークフロー図:")
        print(agent.get_workflow_diagram())
        
        # テスト質問の実行
        test_queries = [
            "楽天グループの総資産を教えてください",
            "ソフトバンクの最新の財務状況を分析して",
            "存在しない企業XYZの情報を教えて",  # エラーケーステスト
        ]
        
        print("\n4. 質問応答テスト:")
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- テスト {i} ---")
            print(f"質問: {query}")
            
            try:
                result = agent.invoke(query)
                print(f"実行時間: {result.get('execution_time', 0):.2f}秒")
                print(f"企業名: {result.get('company_name', 'N/A')}")
                print(f"次のアクション: {result.get('next_action', 'N/A')}")
                
                if result.get("error_message"):
                    print(f"⚠️  エラー: {result['error_message']}")
                
                print(f"回答: {result.get('final_answer', 'N/A')[:200]}...")
                
            except Exception as e:
                print(f"❌ エラー: {str(e)}")
        
        print("\n5. ストリーミングテスト:")
        print("質問: 楽天の情報を教えて")
        try:
            for chunk in agent.stream("楽天の情報を教えて"):
                for node_name, node_data in chunk.items():
                    print(f"[{node_name}] 処理中...")
                    if node_data.get("final_answer"):
                        print(f"最終回答: {node_data['final_answer'][:100]}...")
                        break
        except Exception as e:
            print(f"❌ ストリーミングエラー: {str(e)}")
            
    except Exception as e:
        print(f"❌ 全体エラー: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_agent()