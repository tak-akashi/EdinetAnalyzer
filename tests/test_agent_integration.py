import pytest
import json
import os
from unittest.mock import patch, MagicMock


class TestAgentToolsIntegration:
    """エージェントとツールの統合テスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        pass
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_edinet_search_tool_integration(self, mock_api_class):
        """EdinetSearchToolとの統合テスト"""
        # モックAPI設定
        mock_api = MagicMock()
        mock_api.get_documents_list.return_value = {
            "results": [{
                "docID": "S100TEST",
                "filerName": "テスト企業",
                "docDescription": "有価証券報告書",
                "xbrlFlag": "1",
                "submitDateTime": "2024-07-10T15:00:00"
            }]
        }
        mock_api_class.return_value = mock_api
        
        # ツールのインポートとテスト
        from src.edinet_analyzer.langchain_tools import EdinetSearchTool
        
        tool = EdinetSearchTool()
        result = tool._run("テスト企業", "2024-07-10", "有価証券報告書")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["company_name"] == "テスト企業"
        assert len(result_data["documents"]) == 1
        assert result_data["documents"][0]["docID"] == "S100TEST"
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_edinet_download_tool_integration(self, mock_api_class):
        """EdinetDownloadToolとの統合テスト"""
        # モックAPI設定
        mock_api = MagicMock()
        mock_api.download_xbrl_document.return_value = "temp_downloads/S100TEST_xbrl.zip"
        mock_api_class.return_value = mock_api
        
        # ツールのインポートとテスト
        from src.edinet_analyzer.langchain_tools import EdinetDownloadTool
        
        tool = EdinetDownloadTool()
        result = tool._run("S100TEST", "xbrl")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["doc_id"] == "S100TEST"
        assert result_data["document_type"] == "xbrl"
        assert "temp_downloads/S100TEST_xbrl.zip" in result_data["file_path"]
    
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    def test_xbrl_analysis_tool_integration(self, mock_parser_class, mock_exists):
        """XbrlAnalysisToolとの統合テスト"""
        # ファイル存在モック
        mock_exists.return_value = True
        
        # パーサーモック設定
        mock_parser = MagicMock()
        mock_parser.extract_xbrl_data.return_value = {
            "company_type": "investment_trust",
            "total_elements": 100,
            "financial_data": {
                "total_assets": {
                    "value": 1000000000,
                    "formatted_value": "10億円",
                    "display_name": "総資産",
                    "item_code": "jppfs_cor:Assets"
                }
            },
            "summary_report": "テスト分析レポート"
        }
        mock_parser_class.return_value = mock_parser
        
        # ツールのインポートとテスト
        from src.edinet_analyzer.langchain_tools import XbrlAnalysisTool
        
        tool = XbrlAnalysisTool()
        result = tool._run("test_file.zip", "financial")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["analysis_type"] == "financial"
        assert result_data["company_type"] == "investment_trust"
        assert "financial_data" in result_data
        assert result_data["extracted_count"] == 1
    
    def test_tool_schema_validation(self):
        """ツールスキーマの検証テスト"""
        with patch.dict(os.environ, {"EDINET_API_KEY": "test_key"}):
            from src.edinet_analyzer.langchain_tools import (
                EdinetSearchTool, EdinetDownloadTool, 
                XbrlAnalysisTool, XbrlComparisonTool
            )
            
            # 各ツールの基本プロパティ確認
            search_tool = EdinetSearchTool()
            assert search_tool.name == "edinet_search"
            assert search_tool.description is not None
            assert search_tool.args_schema is not None
            
            download_tool = EdinetDownloadTool()
            assert download_tool.name == "edinet_download"
            assert download_tool.description is not None
            assert download_tool.args_schema is not None
            
            analysis_tool = XbrlAnalysisTool()
            assert analysis_tool.name == "xbrl_analysis"
            assert analysis_tool.description is not None
            assert analysis_tool.args_schema is not None
            
            comparison_tool = XbrlComparisonTool()
            assert comparison_tool.name == "xbrl_comparison"
            assert comparison_tool.description is not None
            assert comparison_tool.args_schema is not None
    
    def test_tool_error_handling(self):
        """ツールエラーハンドリングテスト"""
        with patch.dict(os.environ, {"EDINET_API_KEY": "test_key"}):
            from src.edinet_analyzer.langchain_tools import XbrlAnalysisTool
            
            tool = XbrlAnalysisTool()
            
            # 存在しないファイルに対するエラーハンドリング
            result = tool._run("non_existent_file.zip")
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error"] == "FileNotFound"
            assert "見つかりません" in result_data["message"]
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    def test_end_to_end_tool_workflow(self, mock_exists, mock_parser_class, mock_api_class):
        """エンドツーエンドツールワークフローテスト"""
        # API モック設定
        mock_api = MagicMock()
        mock_api.get_documents_list.return_value = {
            "results": [{
                "docID": "S100TEST",
                "filerName": "テスト企業",
                "docDescription": "有価証券報告書",
                "xbrlFlag": "1"
            }]
        }
        mock_api.download_xbrl_document.return_value = "temp_downloads/S100TEST_xbrl.zip"
        mock_api_class.return_value = mock_api
        
        # パーサーモック設定
        mock_exists.return_value = True
        mock_parser = MagicMock()
        mock_parser.extract_xbrl_data.return_value = {
            "company_type": "investment_trust",
            "total_elements": 100,
            "financial_data": {
                "total_assets": {
                    "value": 1000000000,
                    "formatted_value": "10億円",
                    "display_name": "総資産"
                }
            }
        }
        mock_parser_class.return_value = mock_parser
        
        # ツールの順次実行
        from src.edinet_analyzer.langchain_tools import (
            EdinetSearchTool, EdinetDownloadTool, XbrlAnalysisTool
        )
        
        # 1. 検索
        search_tool = EdinetSearchTool()
        search_result = search_tool._run("テスト企業", "2024-07-10", "有価証券報告書")
        search_data = json.loads(search_result)
        
        assert search_data["success"] is True
        doc_id = search_data["documents"][0]["docID"]
        
        # 2. ダウンロード
        download_tool = EdinetDownloadTool()
        download_result = download_tool._run(doc_id, "xbrl")
        download_data = json.loads(download_result)
        
        assert download_data["success"] is True
        file_path = download_data["file_path"]
        
        # 3. 解析
        analysis_tool = XbrlAnalysisTool()
        analysis_result = analysis_tool._run(file_path, "financial")
        analysis_data = json.loads(analysis_result)
        
        assert analysis_data["success"] is True
        assert "financial_data" in analysis_data
        # フォーマットされた値が含まれていることを確認
        financial_data_str = str(analysis_data["financial_data"])
        assert "億円" in financial_data_str
    
    def test_tool_json_output_consistency(self):
        """ツールJSON出力の一貫性テスト"""
        with patch.dict(os.environ, {"EDINET_API_KEY": "test_key"}):
            from src.edinet_analyzer.langchain_tools import XbrlAnalysisTool
            
            tool = XbrlAnalysisTool()
            
            # 存在しないファイルの場合
            result = tool._run("non_existent.zip")
            data = json.loads(result)
            
            # すべてのツールが同じ基本構造を持つことを確認
            required_fields = ["success"]
            for field in required_fields:
                assert field in data
            
            # エラー時の構造確認
            assert data["success"] is False
            assert "error" in data
            assert "message" in data


class TestAgentPerformance:
    """エージェントパフォーマンステスト"""
    
    def test_response_time_measurement(self):
        """応答時間測定テスト"""
        import time
        from tests.test_agent_basic import MockEdinetAnalysisAgent
        
        agent = MockEdinetAnalysisAgent()
        
        start_time = time.time()
        result = agent.invoke("楽天の総資産を教えてください")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 基本的な応答時間チェック（モックなので非常に高速）
        assert response_time < 1.0  # 1秒以内
        assert result.get("execution_time") is not None
        assert result["execution_time"] <= response_time
    
    def test_memory_usage_basic(self):
        """基本的なメモリ使用量テスト"""
        import psutil
        import os
        from tests.test_agent_basic import MockEdinetAnalysisAgent
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        agent = MockEdinetAnalysisAgent()
        
        # 複数の質問を処理
        queries = [
            "楽天の総資産を教えて",
            "ソフトバンクの業績は？",
            "トヨタの財務状況を分析して"
        ]
        
        for query in queries:
            result = agent.invoke(query)
            assert result["final_answer"] is not None
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加量が合理的範囲内であることを確認（10MB以下）
        assert memory_increase < 10 * 1024 * 1024
    
    def test_concurrent_request_handling(self):
        """並行リクエスト処理テスト"""
        import threading
        import time
        from tests.test_agent_basic import MockEdinetAnalysisAgent
        
        agent = MockEdinetAnalysisAgent()
        results = []
        errors = []
        
        def process_query(query, index):
            try:
                result = agent.invoke(f"{query} #{index}")
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # 5つの並行リクエストを作成
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=process_query,
                args=("楽天の総資産を教えて", i)
            )
            threads.append(thread)
        
        # 全スレッド開始
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 全スレッド完了待ち
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # 結果検証
        assert len(errors) == 0, f"エラーが発生しました: {errors}"
        assert len(results) == 5
        assert all(result["final_answer"] is not None for result in results)
        
        # 並行処理時間が合理的であることを確認
        total_time = end_time - start_time
        assert total_time < 2.0  # 2秒以内


@pytest.mark.integration
class TestAgentRealWorldScenarios:
    """実世界シナリオテスト"""
    
    def test_various_query_patterns(self):
        """様々な質問パターンテスト"""
        from tests.test_agent_basic import MockEdinetAnalysisAgent
        
        agent = MockEdinetAnalysisAgent()
        
        query_patterns = [
            # 基本的な質問
            "楽天の総資産を教えてください",
            
            # 詳細な質問
            "楽天グループ株式会社の最新の有価証券報告書から総資産額と純利益を教えてください",
            
            # 比較的な質問
            "ソフトバンクとトヨタの財務状況を比較してください",
            
            # 分析要求
            "楽天の財務データを詳細に分析してください",
            
            # 短い質問
            "楽天の売上は？",
            
            # 敬語を含む質問
            "恐れ入りますが、トヨタ自動車の業績について教えていただけますでしょうか"
        ]
        
        for query in query_patterns:
            result = agent.invoke(query)
            
            # 基本的な結果検証
            assert result is not None
            assert result["query"] == query
            assert result["final_answer"] is not None
            assert len(result["final_answer"]) > 0
    
    def test_error_scenarios(self):
        """エラーシナリオテスト"""
        from tests.test_agent_basic import MockEdinetAnalysisAgent
        
        agent = MockEdinetAnalysisAgent()
        
        error_scenarios = [
            # 存在しない企業
            "存在しない企業XYZの財務状況を教えて",
            
            # 空の質問
            "",
            
            # 非常に短い質問
            "楽",
            
            # 関係ない質問
            "今日の天気はどうですか？",
            
            # 特殊文字を含む質問
            "楽天@#$%の財務状況は？",
        ]
        
        for query in error_scenarios:
            result = agent.invoke(query)
            
            # エラーケースでも適切に処理されることを確認
            assert result is not None
            assert result["query"] == query
            assert result["final_answer"] is not None
    
    def test_japanese_language_handling(self):
        """日本語処理テスト"""
        from tests.test_agent_basic import MockEdinetAnalysisAgent
        
        agent = MockEdinetAnalysisAgent()
        
        japanese_patterns = [
            # ひらがな
            "らくてんのそうしさんをおしえて",
            
            # カタカナ
            "ラクテンノザイムジョウキョウヲブンセキシテ",
            
            # 漢字
            "楽天総資産額教",
            
            # 混合
            "楽天グループの総資産をお教えください",
            
            # 長い文章
            "楽天グループ株式会社の最新の有価証券報告書に記載されている総資産額について詳細な説明をお願いいたします"
        ]
        
        for query in japanese_patterns:
            result = agent.invoke(query)
            
            assert result is not None
            assert result["final_answer"] is not None
            # 日本語の回答が含まれていることを確認
            assert any(ord(char) > 127 for char in result["final_answer"])  # 非ASCII文字が含まれている