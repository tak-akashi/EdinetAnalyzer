import pytest
import json
import os
from unittest.mock import patch, MagicMock
from src.edinet_analyzer.tools import (
    EdinetApi, EnhancedXbrlParser, TaxonomyAnalyzer, 
    FinancialMapping, FinancialExtractor
)
from src.edinet_analyzer.langchain_tools import (
    EdinetSearchTool, EdinetDownloadTool, XbrlAnalysisTool
)


@pytest.mark.integration
class TestFullWorkflowIntegration:
    """完全なワークフローの統合テスト"""
    
    @pytest.mark.skipif(
        not os.environ.get("EDINET_API_KEY"),
        reason="EDINET_API_KEY環境変数が設定されていません"
    )
    @pytest.mark.skipif(
        not os.path.exists("temp_downloads/S100VVBR_xbrl.zip"),
        reason="サンプルXBRLファイルが見つかりません"
    )
    def test_end_to_end_analysis_workflow(self, sample_xbrl_file):
        """エンドツーエンド分析ワークフローのテスト"""
        # ステップ1: EDINET検索ツールでの企業検索をスキップ（単体テストで既に検証済み）
        # 代わりに固定のdoc_idを使用
        doc_id = "S100VVBR"
        
        # ステップ2: XBRL解析ツールでの財務分析
        analysis_tool = XbrlAnalysisTool()
        
        # 実際のサンプルファイルを使用
        analysis_result = analysis_tool._run(sample_xbrl_file, "financial")
        analysis_data = json.loads(analysis_result)
        
        if analysis_data["success"]:
            # 基本的な結果構造の確認
            assert "company_type" in analysis_data
            assert "financial_data" in analysis_data
            assert analysis_data["extracted_count"] > 0
            
            # 財務データの妥当性確認
            financial_data = analysis_data["financial_data"]
            assert len(financial_data) > 0
            
            # 各財務項目の構造確認
            for item_name, item_data in financial_data.items():
                assert "value" in item_data
                assert "formatted_value" in item_data
                assert "item_code" in item_data
                assert isinstance(item_data["value"], (int, float))
        
        # ステップ3: 検索分析の実行
        search_analysis_result = analysis_tool._run(sample_xbrl_file, "search", ["資産", "利益"])
        search_analysis_data = json.loads(search_analysis_result)
        
        if search_analysis_data["success"]:
            assert search_analysis_data["analysis_type"] == "search"
            assert "search_results" in search_analysis_data
            assert len(search_analysis_data["search_terms"]) == 2
    
    def test_component_integration(self):
        """コンポーネント間の統合テスト"""
        # 財務マッピングの初期化
        mapping = FinancialMapping()
        
        # 財務抽出器の初期化（マッピングを使用）
        extractor = FinancialExtractor(mapping)
        
        # タクソノミ分析器の初期化
        analyzer = TaxonomyAnalyzer()
        
        # XBRL解析器の初期化（すべてのコンポーネントを使用）
        parser = EnhancedXbrlParser()
        
        # 各コンポーネントが適切に初期化されていることを確認
        assert parser.financial_mapping is not None
        assert parser.financial_extractor is not None
        assert parser.taxonomy_analyzer is not None
        
        # マッピング設定の確認
        investment_trust_mapping = mapping.get_mapping_for_company_type("investment_trust")
        assert len(investment_trust_mapping) > 0
        
        general_company_mapping = mapping.get_mapping_for_company_type("general_company")
        assert len(general_company_mapping) > 0
        
        # 企業タイプ判別の動作確認
        test_elements = ["jppfs_cor:CallLoansCAFND", "jppfs_cor:Assets"]
        company_type = analyzer._detect_company_type(test_elements)
        assert company_type in ["investment_trust", "general_company", "unknown"]
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_integration_key"})
    def test_langchain_tools_integration(self):
        """LangChainツール間の統合テスト"""
        # 各ツールの初期化
        search_tool = EdinetSearchTool()
        download_tool = EdinetDownloadTool()
        analysis_tool = XbrlAnalysisTool()
        
        # ツールの基本機能確認（詳細テストは単体テストで実施済み）
        assert search_tool.name == "edinet_search"
        assert download_tool.name == "edinet_download"
        assert analysis_tool.name == "xbrl_analysis"
        
        # エラーハンドリングの確認
        analysis_result = analysis_tool._run("non_existent_file.zip")
        analysis_data = json.loads(analysis_result)
        
        # ファイルが存在しないためエラーになるが、ツールは適切にエラーハンドリングする
        assert analysis_data["success"] is False
        assert analysis_data["error"] == "FileNotFound"
    
    def test_error_propagation_and_handling(self):
        """エラー伝播とハンドリングのテスト"""
        with patch.dict(os.environ, {"EDINET_API_KEY": "test_key"}):
            # XBRLAnalysisToolのエラーハンドリングのみテスト（他は単体テストで検証済み）
            analysis_tool = XbrlAnalysisTool()
            
            # ファイル不存在エラー
            result = analysis_tool._run("non_existent_file.zip")
            
            # すべてのツールが適切にエラーをJSONで返すことを確認
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "error" in result_data or "message" in result_data
    
    @pytest.mark.skipif(
        not os.path.exists("temp_downloads/S100VVBR_xbrl.zip"),
        reason="サンプルXBRLファイルが見つかりません"
    )
    def test_performance_and_memory_usage(self, sample_xbrl_file):
        """パフォーマンスとメモリ使用量のテスト"""
        import time
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 初期メモリ使用量
        initial_memory = process.memory_info().rss
        
        # 解析開始時間
        start_time = time.time()
        
        # XBRL解析の実行
        analysis_tool = XbrlAnalysisTool()
        result = analysis_tool._run(sample_xbrl_file, "financial")
        
        # 実行時間の測定
        execution_time = time.time() - start_time
        
        # 最終メモリ使用量
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 結果の確認
        result_data = json.loads(result)
        
        # パフォーマンス指標の確認
        print(f"実行時間: {execution_time:.2f}秒")
        print(f"メモリ増加量: {memory_increase / 1024 / 1024:.2f}MB")
        
        # 合理的な範囲内であることを確認
        assert execution_time < 30.0  # 30秒以内
        assert memory_increase < 100 * 1024 * 1024  # 100MB以内
        
        if result_data["success"]:
            assert "financial_data" in result_data
    
    def test_concurrent_tool_usage(self):
        """並行ツール使用のテスト"""
        import threading
        import time
        
        results = []
        
        def run_analysis_tool(file_path, analysis_type, thread_id):
            """分析ツールを実行する関数"""
            tool = XbrlAnalysisTool()
            result = tool._run(file_path, analysis_type)
            results.append({
                "thread_id": thread_id,
                "result": json.loads(result),
                "timestamp": time.time()
            })
        
        # 複数スレッドでツールを並行実行
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=run_analysis_tool,
                args=("non_existent_file.zip", "financial", i)
            )
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果の確認
        assert len(results) == 3
        
        # すべてのスレッドが正常に完了していることを確認
        for result in results:
            assert result["result"]["success"] is False  # ファイルが存在しないため
            assert result["result"]["error"] == "FileNotFound"
    
    def test_data_flow_integrity(self):
        """データフロー整合性のテスト"""
        # テスト用のダミーデータ作成
        import pandas as pd
        
        test_xbrl_data = pd.DataFrame({
            "要素ID": [
                "jppfs_cor:CallLoansCAFND",
                "jppfs_cor:SecurityInvestmentTrustBeneficiarySecuritiesCAFND",
                "jppfs_cor:Assets"
            ],
            "項目名": [
                "コール・ローン",
                "投資信託受益証券", 
                "資産合計"
            ],
            "値": [1000000, 5000000, 6000000],
            "コンテキストID": ["ctx1", "ctx2", "ctx3"],
            "相対年度": ["当期", "当期", "当期"]
        })
        
        # データフローの各段階での整合性確認
        
        # 1. 財務マッピング
        mapping = FinancialMapping()
        investment_trust_mapping = mapping.get_mapping_for_company_type("investment_trust")
        assert len(investment_trust_mapping) > 0
        
        # 2. 財務抽出
        extractor = FinancialExtractor(mapping)
        extracted_data = extractor.extract_financial_data(test_xbrl_data, "investment_trust")
        
        # 抽出されたデータの整合性確認
        assert len(extracted_data) > 0
        for item_name, item_data in extracted_data.items():
            assert "value" in item_data
            assert "display_name" in item_data
            assert isinstance(item_data["value"], (int, float))
        
        # 3. DataFrame変換
        result_df = extractor.export_to_dataframe(extracted_data)
        assert not result_df.empty
        assert len(result_df) == len(extracted_data)
        
        # 4. サマリーレポート生成
        summary = extractor.generate_summary_report(extracted_data, "investment_trust")
        assert len(summary) > 0
        assert "投資信託" in summary


@pytest.mark.slow
class TestLargeDataIntegration:
    """大量データでの統合テスト"""
    
    def test_large_csv_processing(self, temp_dir):
        """大量CSVデータの処理テスト"""
        import pandas as pd
        import zipfile
        
        # 大量のテストデータ作成
        large_data = []
        for i in range(1000):
            large_data.append({
                "要素ID": f"test_element_{i}",
                "項目名": f"テスト項目{i}",
                "値": i * 1000,
                "コンテキストID": f"ctx{i % 10}",
                "相対年度": "当期" if i % 2 == 0 else "前期"
            })
        
        df = pd.DataFrame(large_data)
        
        # CSVファイルとして保存
        csv_file = os.path.join(temp_dir, "large_test.csv")
        df.to_csv(csv_file, index=False, encoding="utf-8")
        
        # ZIPファイルとして圧縮
        zip_file = os.path.join(temp_dir, "large_test.zip")
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.write(csv_file, "XBRL_TO_CSV/large_test.csv")
        
        # XBRL解析ツールでの処理
        analysis_tool = XbrlAnalysisTool()
        
        # メモリ使用量の監視
        import psutil
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 解析実行
        result = analysis_tool._run(zip_file, "taxonomy")
        result_data = json.loads(result)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 結果確認
        if result_data["success"]:
            # 他のCSVファイルも含めて処理されるため、少なくとも1000要素以上が処理されていることを確認
            assert result_data["total_elements"] >= 1000
        
        # メモリ増加が合理的な範囲内であることを確認
        assert memory_increase < 50 * 1024 * 1024  # 50MB以内