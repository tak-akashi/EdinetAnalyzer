#!/usr/bin/env python3
"""
EDINET分析エージェントの対話的テストスクリプト
"""

import os
import sys
from dotenv import load_dotenv
from src.edinet_analyzer import create_agent

# .envファイルを読み込み
load_dotenv()

def interactive_test():
    """対話的テスト"""
    
    print("=" * 60)
    print("EDINET分析エージェント 対話的テスト")
    print("=" * 60)
    print("注意: このテストにはOpenAI APIキーとEDINET APIキーが必要です")
    print("'quit'または'exit'で終了します")
    print("=" * 60)
    
    # APIキーの確認
    openai_key = os.environ.get("OPENAI_API_KEY")
    edinet_key = os.environ.get("EDINET_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY環境変数が設定されていません")
        openai_key = input("OpenAI APIキーを入力してください（テスト用の場合は'test'と入力）: ")
        if openai_key and openai_key != 'test':
            os.environ["OPENAI_API_KEY"] = openai_key
        else:
            os.environ["OPENAI_API_KEY"] = "test_key_for_demo"
    
    if not edinet_key:
        print("❌ EDINET_API_KEY環境変数が設定されていません")
        edinet_key = input("EDINET APIキーを入力してください（テスト用の場合は'test'と入力）: ")
        if edinet_key and edinet_key != 'test':
            os.environ["EDINET_API_KEY"] = edinet_key
        else:
            os.environ["EDINET_API_KEY"] = "test_key_for_demo"
    
    try:
        print("\n🤖 エージェントを初期化中...")
        agent = create_agent(enable_memory=True)
        print("✅ エージェントの初期化が完了しました")
        
        # 環境検証
        validation = agent.validate_environment()
        print("\n📋 環境検証結果:")
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}")
        
        print("\n💡 使用例:")
        print("  - 楽天グループの総資産を教えてください")
        print("  - ソフトバンクの最新の財務状況は？")
        print("  - トヨタ自動車の業績を分析して")
        print()
        
        # 対話ループ
        session_id = "interactive_session"
        config = {"configurable": {"thread_id": session_id}}
        
        while True:
            try:
                query = input("\n🗣️  質問を入力してください: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q', '終了']:
                    print("👋 テストを終了します")
                    break
                
                if not query:
                    print("⚠️  質問を入力してください")
                    continue
                
                print(f"\n🔍 質問を処理中: {query}")
                print("-" * 40)
                
                # ストリーミング実行で進行状況を表示
                final_result = None
                for chunk in agent.stream(query, config=config):
                    for node_name, node_data in chunk.items():
                        if node_name != "__end__":
                            print(f"📍 [{node_name}] 処理中...")
                            
                            # 中間結果の表示
                            if node_data.get("company_name"):
                                print(f"   企業名: {node_data['company_name']}")
                            if node_data.get("search_results"):
                                print(f"   検索結果: {len(node_data['search_results'])}件の書類が見つかりました")
                            if node_data.get("downloaded_files"):
                                print(f"   ダウンロード: {len(node_data['downloaded_files'])}件のファイルをダウンロードしました")
                            if node_data.get("xbrl_analysis"):
                                print(f"   解析完了: 財務データを解析しました")
                            if node_data.get("final_answer"):
                                final_result = node_data
                                break
                
                print("-" * 40)
                
                if final_result and final_result.get("final_answer"):
                    print("🤖 回答:")
                    print(final_result["final_answer"])
                    
                    if final_result.get("execution_time"):
                        print(f"\n⏱️  実行時間: {final_result['execution_time']:.2f}秒")
                else:
                    print("❌ 回答を生成できませんでした")
                
            except KeyboardInterrupt:
                print("\n\n👋 Ctrl+Cで中断されました")
                break
            except Exception as e:
                print(f"❌ エラーが発生しました: {str(e)}")
                continue
    
    except Exception as e:
        print(f"❌ 初期化エラー: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    interactive_test()