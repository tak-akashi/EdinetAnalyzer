import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from src.edinet_analyzer.langchain_tools.edinet_search_tool import (
    EdinetSearchTool, EdinetDownloadTool, EdinetSearchInput, EdinetDownloadInput
)
from src.edinet_analyzer.langchain_tools.xbrl_analysis_tool import (
    XbrlAnalysisTool, XbrlComparisonTool, XbrlAnalysisInput, XbrlComparisonInput
)


class TestEdinetSearchTool:
    """EDINET検索ツールのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        # 環境変数パッチは各テストメソッドで適用する必要がある
        pass
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    def test_tool_properties(self):
        """ツールプロパティのテスト"""
        tool = EdinetSearchTool()
        assert tool.name == "edinet_search"
        assert "EDINET API" in tool.description
        assert tool.args_schema == EdinetSearchInput
    
    def test_input_schema(self):
        """入力スキーマのテスト"""
        # 有効な入力
        valid_input = EdinetSearchInput(
            company_name="楽天",
            date="2024-07-10",
            document_type="有価証券報告書"
        )
        assert valid_input.company_name == "楽天"
        assert valid_input.date == "2024-07-10"
        assert valid_input.document_type == "有価証券報告書"
        
        # 最小限の入力
        minimal_input = EdinetSearchInput(company_name="テスト企業")
        assert minimal_input.company_name == "テスト企業"
        assert minimal_input.date is None
        assert minimal_input.document_type == "有価証券報告書"
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_run_success(self, mock_api_class, sample_edinet_response):
        """検索成功時のテスト"""
        # モックの設定
        mock_api = MagicMock()
        mock_api.get_documents_list.return_value = sample_edinet_response
        mock_api_class.return_value = mock_api
        
        # ツール初期化（パッチ適用後）
        tool = EdinetSearchTool()
        
        # ツールの実行
        result = tool._run("テスト企業", "2024-07-10", "有価証券報告書")
        
        # 結果の確認
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["company_name"] == "テスト企業"
        assert result_data["total_found"] >= 0
        assert "documents" in result_data
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_run_api_error(self, mock_api_class):
        """API エラー時のテスト"""
        # モックの設定
        mock_api = MagicMock()
        mock_api.get_documents_list.return_value = None
        mock_api_class.return_value = mock_api
        
        # ツール初期化
        tool = EdinetSearchTool()
        
        # ツールの実行
        result = tool._run("テスト企業")
        
        # 結果の確認
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "失敗" in result_data["message"]
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_run_exception(self, mock_api_class):
        """例外発生時のテスト"""
        # モックの設定
        mock_api = MagicMock()
        mock_api.get_documents_list.side_effect = Exception("テストエラー")
        mock_api_class.return_value = mock_api
        
        # ツール初期化
        tool = EdinetSearchTool()
        
        # ツールの実行
        result = tool._run("テスト企業")
        
        # 結果の確認
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "テストエラー" in result_data["error"]
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_company_name_filtering(self, mock_api_class, sample_edinet_response):
        """企業名フィルタリングのテスト"""
        # テスト用の複数企業データ
        multi_company_response = {
            "results": [
                {
                    "docID": "S100001",
                    "filerName": "テスト株式会社",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2024-07-10T15:00:00"
                },
                {
                    "docID": "S100002", 
                    "filerName": "別の企業株式会社",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2024-07-10T16:00:00"
                },
                {
                    "docID": "S100003",
                    "filerName": "テスト関連会社",
                    "docDescription": "有価証券報告書", 
                    "submitDateTime": "2024-07-10T17:00:00"
                }
            ]
        }
        
        mock_api = MagicMock()
        mock_api.get_documents_list.return_value = multi_company_response
        mock_api_class.return_value = mock_api
        
        # ツール初期化
        tool = EdinetSearchTool()
        
        # "テスト"を含む企業を検索
        result = tool._run("テスト")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        # "テスト"を含む企業のみが返される
        assert result_data["total_found"] == 2  # テスト株式会社とテスト関連会社
        
        for doc in result_data["documents"]:
            assert "テスト" in doc["filerName"]


class TestEdinetDownloadTool:
    """EDINET ダウンロードツールのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        pass
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    def test_tool_properties(self):
        """ツールプロパティのテスト"""
        tool = EdinetDownloadTool()
        assert tool.name == "edinet_download"
        assert "ダウンロード" in tool.description
        assert tool.args_schema == EdinetDownloadInput
    
    def test_input_schema(self):
        """入力スキーマのテスト"""
        # XBRL ダウンロード
        xbrl_input = EdinetDownloadInput(doc_id="S100TEST", document_type="xbrl")
        assert xbrl_input.doc_id == "S100TEST"
        assert xbrl_input.document_type == "xbrl"
        
        # メインドキュメントダウンロード
        main_input = EdinetDownloadInput(doc_id="S100TEST", document_type="main")
        assert main_input.document_type == "main"
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_run_xbrl_success(self, mock_api_class):
        """XBRL ダウンロード成功のテスト"""
        mock_api = MagicMock()
        mock_api.download_xbrl_document.return_value = "temp_downloads/S100TEST_xbrl.zip"
        mock_api_class.return_value = mock_api
        
        tool = EdinetDownloadTool()
        result = tool._run("S100TEST", "xbrl")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["doc_id"] == "S100TEST"
        assert result_data["document_type"] == "xbrl"
        assert "temp_downloads/S100TEST_xbrl.zip" in result_data["file_path"]
    
    @patch.dict(os.environ, {"EDINET_API_KEY": "test_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_run_download_failure(self, mock_api_class):
        """ダウンロード失敗のテスト"""
        mock_api = MagicMock()
        mock_api.download_xbrl_document.return_value = None
        mock_api_class.return_value = mock_api
        
        tool = EdinetDownloadTool()
        result = tool._run("S100TEST", "xbrl")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "失敗" in result_data["message"]


class TestXbrlAnalysisTool:
    """XBRL解析ツールのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        pass
    
    def test_tool_properties(self):
        """ツールプロパティのテスト"""
        tool = XbrlAnalysisTool()
        assert tool.name == "xbrl_analysis"
        assert "XBRL" in tool.description
        assert tool.args_schema == XbrlAnalysisInput
    
    def test_input_schema(self):
        """入力スキーマのテスト"""
        # 基本的な財務分析
        basic_input = XbrlAnalysisInput(file_path="test.zip")
        assert basic_input.file_path == "test.zip"
        assert basic_input.analysis_type == "financial"
        assert basic_input.search_terms is None
        
        # 検索分析
        search_input = XbrlAnalysisInput(
            file_path="test.zip",
            analysis_type="search",
            search_terms=["資産", "利益"]
        )
        assert search_input.analysis_type == "search"
        assert search_input.search_terms == ["資産", "利益"]
    
    def test_run_file_not_found(self):
        """ファイルが見つからない場合のテスト"""
        tool = XbrlAnalysisTool()
        result = tool._run("non_existent_file.zip")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert result_data["error"] == "FileNotFound"
        assert "見つかりません" in result_data["message"]
    
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    def test_run_analysis_error(self, mock_parser_class, mock_exists):
        """解析エラーのテスト"""
        mock_exists.return_value = True
        mock_parser = MagicMock()
        mock_parser.extract_xbrl_data.return_value = None
        mock_parser_class.return_value = mock_parser
        
        tool = XbrlAnalysisTool()
        result = tool._run("test.zip")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert result_data["error"] == "AnalysisError"
    
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    def test_run_financial_analysis_success(self, mock_parser_class, mock_exists, sample_financial_data):
        """財務分析成功のテスト"""
        mock_exists.return_value = True
        mock_parser = MagicMock()
        mock_parser.extract_xbrl_data.return_value = {
            "company_type": "investment_trust",
            "total_elements": 100,
            "financial_data": sample_financial_data,
            "summary_report": "テストレポート"
        }
        mock_parser_class.return_value = mock_parser
        
        tool = XbrlAnalysisTool()
        result = tool._run("test.zip", "financial")
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["analysis_type"] == "financial"
        assert result_data["company_type"] == "investment_trust"
        assert result_data["extracted_count"] == len(sample_financial_data)
        assert "financial_data" in result_data
    
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    def test_run_search_analysis(self, mock_parser_class, mock_exists):
        """検索分析のテスト"""
        mock_exists.return_value = True
        mock_parser = MagicMock()
        mock_parser.extract_xbrl_data.return_value = {
            "company_type": "investment_trust",
            "total_elements": 100
        }
        
        # 空のDataFrameを返すモック
        import pandas as pd
        mock_parser.search_financial_items.return_value = pd.DataFrame()
        mock_parser_class.return_value = mock_parser
        
        tool = XbrlAnalysisTool()
        result = tool._run("test.zip", "search", ["資産"])
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["analysis_type"] == "search"
        assert result_data["search_terms"] == ["資産"]
    
    def test_format_currency(self):
        """通貨フォーマットのテスト"""
        tool = XbrlAnalysisTool()
        
        # 億円
        assert "億円" in tool._format_currency(1_500_000_000)
        
        # 百万円
        assert "百万円" in tool._format_currency(50_000_000)
        
        # 千円
        assert "千円" in tool._format_currency(500_000)
        
        # 円
        assert "円" in tool._format_currency(500)
        
        # None値
        assert tool._format_currency(None) == "N/A"


class TestXbrlComparisonTool:
    """XBRL比較ツールのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        pass
    
    def test_tool_properties(self):
        """ツールプロパティのテスト"""
        tool = XbrlComparisonTool()
        assert tool.name == "xbrl_comparison"
        assert "比較" in tool.description
        assert tool.args_schema == XbrlComparisonInput
    
    def test_input_schema(self):
        """入力スキーマのテスト"""
        comparison_input = XbrlComparisonInput(
            file_paths=["file1.zip", "file2.zip"],
            comparison_items=["資産合計", "純資産"]
        )
        assert len(comparison_input.file_paths) == 2
        assert comparison_input.comparison_items == ["資産合計", "純資産"]
    
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    def test_run_file_not_found(self, mock_exists):
        """ファイルが見つからない場合のテスト"""
        mock_exists.return_value = False
        
        tool = XbrlComparisonTool()
        result = tool._run(["non_existent1.zip", "non_existent2.zip"])
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["successful_analyses"] == 0
        
        # 個別結果の確認
        for individual_result in result_data["individual_results"]:
            assert individual_result["success"] is False
            assert individual_result["error"] == "FileNotFound"
    
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.os.path.exists')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    def test_run_comparison_success(self, mock_parser_class, mock_exists, sample_financial_data):
        """比較成功のテスト"""
        mock_exists.return_value = True
        
        # 2つのファイルで異なるデータを返すモック
        def mock_extract_side_effect(file_path):
            if "file1" in file_path:
                return {
                    "company_type": "investment_trust",
                    "financial_data": sample_financial_data
                }
            else:
                # 異なる値のデータ
                modified_data = sample_financial_data.copy()
                for key in modified_data:
                    modified_data[key] = modified_data[key].copy()
                    modified_data[key]["value"] *= 1.1  # 10%増加
                return {
                    "company_type": "investment_trust", 
                    "financial_data": modified_data
                }
        
        mock_parser = MagicMock()
        mock_parser.extract_xbrl_data.side_effect = mock_extract_side_effect
        mock_parser_class.return_value = mock_parser
        
        tool = XbrlComparisonTool()
        result = tool._run(["file1.zip", "file2.zip"])
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["total_files"] == 2
        assert result_data["successful_analyses"] == 2
        assert "comparison_analysis" in result_data
    
    def test_perform_comparison_analysis_insufficient_files(self):
        """比較に十分なファイルがない場合のテスト"""
        results = [
            {"success": True, "financial_data": {"item1": 100}},
            {"success": False, "error": "AnalysisError"}
        ]
        
        tool = XbrlComparisonTool()
        analysis = tool._perform_comparison_analysis(results, None)
        assert "error" in analysis
        assert "少なくとも2つ" in analysis["error"]


@pytest.mark.integration
class TestLangChainToolsIntegration:
    """LangChainツールの統合テスト"""
    
    @pytest.mark.skipif(
        not os.path.exists("temp_downloads/S100VVBR_xbrl.zip"),
        reason="サンプルXBRLファイルが見つかりません"
    )
    def test_xbrl_analysis_tool_with_real_file(self, sample_xbrl_file):
        """実際のファイルでのXBRL解析ツールテスト"""
        tool = XbrlAnalysisTool()
        
        # 財務分析の実行
        result = tool._run(sample_xbrl_file, "financial")
        result_data = json.loads(result)
        
        if result_data["success"]:
            assert result_data["analysis_type"] == "financial"
            assert "company_type" in result_data
            assert "financial_data" in result_data
            assert result_data["extracted_count"] > 0
        
        # 検索分析の実行
        search_result = tool._run(sample_xbrl_file, "search", ["資産"])
        search_data = json.loads(search_result)
        
        if search_data["success"]:
            assert search_data["analysis_type"] == "search"
            assert "search_results" in search_data
    
    def test_tool_chain_workflow(self):
        """ツールチェーンワークフローのテスト"""
        # 1. EDINET検索ツールの初期化
        with patch.dict(os.environ, {"EDINET_API_KEY": "test_key"}):
            search_tool = EdinetSearchTool()
            download_tool = EdinetDownloadTool()
            analysis_tool = XbrlAnalysisTool()
        
        # ツールが正しく初期化されていることを確認
        assert search_tool.name == "edinet_search"
        assert download_tool.name == "edinet_download"
        assert analysis_tool.name == "xbrl_analysis"
        
        # 各ツールが適切なスキーマを持つことを確認
        assert hasattr(search_tool, 'args_schema')
        assert hasattr(download_tool, 'args_schema')
        assert hasattr(analysis_tool, 'args_schema')
    
    def test_error_handling_consistency(self):
        """エラーハンドリングの一貫性テスト"""
        tools = []
        
        # 環境変数を設定してツールを初期化
        with patch.dict(os.environ, {"EDINET_API_KEY": "test_key"}):
            tools = [
                EdinetSearchTool(),
                EdinetDownloadTool(), 
                XbrlAnalysisTool(),
                XbrlComparisonTool()
            ]
        
        # すべてのツールが適切にエラーをJSONで返すことを確認
        for tool in tools:
            # 不正な入力でツールを実行
            if hasattr(tool, '_run'):
                try:
                    if tool.name in ["edinet_search", "edinet_download"]:
                        # 例外を発生させる可能性のある操作
                        with patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi') as mock_api_class:
                            mock_api = MagicMock()
                            mock_api.get_documents_list.side_effect = Exception("テストエラー")
                            mock_api.download_xbrl_document.side_effect = Exception("テストエラー")
                            mock_api_class.return_value = mock_api
                            
                            if tool.name == "edinet_search":
                                result = tool._run("テスト企業")
                            else:
                                result = tool._run("S100TEST")
                    else:
                        # XBRL解析ツール
                        result = tool._run("non_existent_file.zip")
                    
                    # 結果がJSONパースできることを確認
                    result_data = json.loads(result)
                    assert "success" in result_data
                    
                except Exception as e:
                    # 予期しない例外が発生した場合はテスト失敗
                    pytest.fail(f"Tool {tool.name} raised unexpected exception: {e}")