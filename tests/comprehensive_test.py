"""
EDINET分析システム総合テスト

実際の企業データを使用して、様々な質問パターンでエージェントの
動作検証と回答精度を評価するためのテストスイート
"""

import os
import time
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

# プロジェクトのルートディレクトリをパスに追加
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from edinet_analyzer import create_agent

# .envファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()


class ComprehensiveTestSuite:
    """総合テストスイート"""
    
    def __init__(self):
        self.results = []
        self.agent = None
        self.test_start_time = None
        
    def setup_agent(self) -> bool:
        """エージェントの初期化"""
        try:
            print("🧠 エージェントを初期化中...")
            self.agent = create_agent(enable_memory=True)
            
            # 環境検証
            validation = self.agent.validate_environment()
            print(f"環境検証結果: {validation}")
            
            if not all(validation.values()):
                print("❌ 環境設定に問題があります")
                return False
                
            print("✅ エージェント初期化成功")
            return True
            
        except Exception as e:
            print(f"❌ エージェント初期化失敗: {e}")
            return False
    
    def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """単一テストケースの実行"""
        test_name = test_case.get("name", "Unknown")
        query = test_case.get("query", "")
        expected_keywords = test_case.get("expected_keywords", [])
        category = test_case.get("category", "general")
        
        print(f"\n📝 テスト実行: {test_name}")
        print(f"質問: {query}")
        
        start_time = time.time()
        result = {
            "name": test_name,
            "category": category,
            "query": query,
            "expected_keywords": expected_keywords,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "execution_time": 0,
            "response": None,
            "error": None,
            "keyword_matches": [],
            "analysis": {}
        }
        
        try:
            # エージェント実行（メモリ機能のためのthread_idを設定）
            config = {"configurable": {"thread_id": f"test_{test_name}"}}
            agent_result = self.agent.invoke(query, config=config)
            execution_time = time.time() - start_time
            
            result["execution_time"] = round(execution_time, 2)
            result["response"] = agent_result
            
            if agent_result and "final_answer" in agent_result:
                result["success"] = True
                final_answer = agent_result["final_answer"]
                
                # キーワードマッチング分析
                for keyword in expected_keywords:
                    if keyword in final_answer:
                        result["keyword_matches"].append(keyword)
                
                # 回答品質分析
                result["analysis"] = self._analyze_response(final_answer, test_case)
                
                print(f"✅ 成功 ({execution_time:.2f}秒)")
                print(f"回答: {final_answer[:200]}{'...' if len(final_answer) > 200 else ''}")
                
            else:
                print("❌ 失敗: 回答が生成されませんでした")
                
        except Exception as e:
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 2)
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            print(f"❌ エラー ({execution_time:.2f}秒): {e}")
        
        return result
    
    def _analyze_response(self, response: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """回答の品質分析"""
        analysis = {
            "length": len(response),
            "has_numbers": any(char.isdigit() for char in response),
            "keyword_coverage": 0,
            "completeness_score": 0
        }
        
        expected_keywords = test_case.get("expected_keywords", [])
        if expected_keywords:
            matched = sum(1 for keyword in expected_keywords if keyword in response)
            analysis["keyword_coverage"] = round(matched / len(expected_keywords), 2)
        
        # 完全性スコア（簡易版）
        completeness_indicators = [
            analysis["has_numbers"],
            analysis["length"] > 100,
            analysis["keyword_coverage"] > 0.5,
            "円" in response or "億円" in response or "兆円" in response,
            "年" in response or "期" in response
        ]
        analysis["completeness_score"] = round(sum(completeness_indicators) / len(completeness_indicators), 2)
        
        return analysis
    
    def get_test_cases(self) -> List[Dict[str, Any]]:
        """テストケースの定義"""
        return [
            # === 大手企業・基本財務データテスト ===
            {
                "name": "楽天グループ_総資産",
                "category": "large_companies",
                "query": "楽天グループの最新の総資産を教えてください",
                "expected_keywords": ["楽天", "総資産", "円", "億円", "兆円"]
            },
            {
                "name": "ソフトバンクグループ_純利益",
                "category": "large_companies", 
                "query": "ソフトバンクグループの純利益を調べてください",
                "expected_keywords": ["ソフトバンク", "純利益", "円", "億円"]
            },
            {
                "name": "トヨタ自動車_売上高",
                "category": "large_companies",
                "query": "トヨタ自動車の最新の売上高はいくらですか？",
                "expected_keywords": ["トヨタ", "売上高", "円", "兆円"]
            },
            {
                "name": "任天堂_財務状況",
                "category": "large_companies",
                "query": "任天堂の財務状況を分析してください",
                "expected_keywords": ["任天堂", "財務", "資産", "利益", "売上"]
            },
            
            # === 企業名表記ゆれテスト ===
            {
                "name": "楽天_表記ゆれ",
                "category": "name_variants",
                "query": "楽天の最新決算について教えて",
                "expected_keywords": ["楽天", "決算", "円"]
            },
            {
                "name": "ソフトバンク_表記ゆれ",
                "category": "name_variants", 
                "query": "ソフトバンクの財務データを分析して",
                "expected_keywords": ["ソフトバンク", "財務", "円"]
            },
            
            # === 複雑な質問テスト ===
            {
                "name": "楽天_複数指標",
                "category": "complex_queries",
                "query": "楽天グループの総資産、純利益、自己資本比率を教えてください",
                "expected_keywords": ["楽天", "総資産", "純利益", "自己資本比率", "円"]
            },
            {
                "name": "財務比率分析",
                "category": "complex_queries",
                "query": "トヨタ自動車の収益性指標（ROE、ROA等）を分析してください",
                "expected_keywords": ["トヨタ", "ROE", "ROA", "収益性", "%"]
            },
            
            # === 中小企業・特殊業界テスト ===
            {
                "name": "ニトリ_小売業",
                "category": "mid_companies",
                "query": "ニトリホールディングスの業績について教えてください",
                "expected_keywords": ["ニトリ", "業績", "売上", "利益"]
            },
            
            # === エラーケーステスト ===
            {
                "name": "存在しない企業",
                "category": "error_cases",
                "query": "架空株式会社の財務データを教えてください",
                "expected_keywords": ["見つかりません", "存在しない", "検索", "エラー"]
            },
            {
                "name": "曖昧な企業名",
                "category": "error_cases", 
                "query": "ABC会社の売上を教えて",
                "expected_keywords": ["特定", "明確", "検索", "見つかりません"]
            },
            
            # === 日付・期間関連テスト ===
            {
                "name": "期間指定",
                "category": "date_queries",
                "query": "楽天グループの最新期の財務データを分析してください",
                "expected_keywords": ["楽天", "最新", "期", "財務"]
            }
        ]
    
    def run_all_tests(self):
        """全テストの実行"""
        print("🚀 EDINET分析システム総合テスト開始")
        print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.test_start_time = time.time()
        
        # エージェント初期化
        if not self.setup_agent():
            print("❌ エージェント初期化に失敗したため、テストを中止します")
            return
        
        # テストケース取得
        test_cases = self.get_test_cases()
        print(f"\n📋 総テストケース数: {len(test_cases)}")
        
        # カテゴリ別実行
        categories = {}
        for test_case in test_cases:
            category = test_case.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(test_case)
        
        print(f"📂 テストカテゴリ: {list(categories.keys())}")
        
        # 各カテゴリでテスト実行
        for category, cases in categories.items():
            print(f"\n{'='*50}")
            print(f"📁 カテゴリ: {category} ({len(cases)}件)")
            print(f"{'='*50}")
            
            for test_case in cases:
                result = self.run_single_test(test_case)
                self.results.append(result)
                
                # 少し待機（APIレート制限対策）
                time.sleep(2)
        
        # 結果サマリー
        self._print_summary()
        self._save_results()
    
    def _print_summary(self):
        """テスト結果サマリーの表示"""
        total_time = time.time() - self.test_start_time
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - successful_tests
        
        print(f"\n{'='*60}")
        print("📊 テスト結果サマリー")
        print(f"{'='*60}")
        print(f"総テスト数: {total_tests}")
        print(f"成功: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"失敗: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"総実行時間: {total_time:.2f}秒")
        print(f"平均実行時間: {total_time/total_tests:.2f}秒/テスト")
        
        # カテゴリ別サマリー
        print(f"\n📂 カテゴリ別結果:")
        categories = {}
        for result in self.results:
            category = result["category"]
            if category not in categories:
                categories[category] = {"total": 0, "success": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["success"] += 1
        
        for category, stats in categories.items():
            success_rate = stats["success"] / stats["total"] * 100
            print(f"  {category}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # 失敗したテストの詳細
        if failed_tests > 0:
            print(f"\n❌ 失敗したテスト:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['name']}: {result.get('error', 'Unknown error')}")
        
        # パフォーマンス分析
        print(f"\n⏱️ パフォーマンス分析:")
        execution_times = [r["execution_time"] for r in self.results if r["execution_time"] > 0]
        if execution_times:
            print(f"  最短: {min(execution_times):.2f}秒")
            print(f"  最長: {max(execution_times):.2f}秒")
            print(f"  平均: {sum(execution_times)/len(execution_times):.2f}秒")
    
    def _save_results(self):
        """テスト結果の保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        
        summary = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "successful_tests": sum(1 for r in self.results if r["success"]),
                "total_time": time.time() - self.test_start_time
            },
            "detailed_results": self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 テスト結果を保存しました: {filename}")


def main():
    """メイン実行関数"""
    # 環境変数チェック
    required_env_vars = ["EDINET_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 必要な環境変数が設定されていません: {missing_vars}")
        print("以下の環境変数を設定してください:")
        for var in missing_vars:
            print(f"  export {var}='your_api_key'")
        return
    
    # テスト実行
    test_suite = ComprehensiveTestSuite()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()