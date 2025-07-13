import pytest
import json
import os
from unittest.mock import patch, MagicMock

from src.edinet_analyzer.agent import EdinetAnalysisAgent, create_agent
from src.edinet_analyzer.state import create_initial_state, EdinetAgentState
from src.edinet_analyzer.nodes import EdinetAgentNodes


class TestEdinetAnalysisAgent:
    """EDINET分析エージェントのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        pass
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    def test_agent_initialization(self):
        """エージェントの初期化テスト"""
        agent = create_agent(enable_memory=False)
        
        assert agent is not None
        assert agent.llm is not None
        assert agent.nodes is not None
        assert agent.workflow is not None
        assert agent.app is not None
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    def test_agent_with_memory(self):
        """メモリ機能付きエージェントのテスト"""
        agent = create_agent(enable_memory=True)
        
        assert agent.checkpointer is not None
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    def test_environment_validation(self):
        """環境検証テスト"""
        agent = create_agent(enable_memory=False)
        
        with patch('src.edinet_analyzer.langchain_tools.EdinetSearchTool'):
            with patch('langchain_openai.ChatOpenAI.invoke', return_value="テスト応答"):
                validation = agent.validate_environment()
                
                assert "edinet_api_key" in validation
                assert "openai_api_key" in validation
                assert "edinet_tools" in validation
                assert "llm_connection" in validation
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    @patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser')
    def test_agent_invoke_success(self, mock_parser_class, mock_api_class):
        """エージェント実行成功テスト"""
        # モックの設定
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
        
        # LLMのモック
        agent = create_agent(enable_memory=False)
        
        with patch('langchain_openai.ChatOpenAI.invoke') as mock_llm:
            # 質問解析のレスポンス
            mock_llm.side_effect = [
                MagicMock(content='{"company_name": "テスト企業", "search_date": "2024-07-10", "document_type": "有価証券報告書", "analysis_type": "financial"}'),
                MagicMock(content="テスト企業の総資産は10億円です。")
            ]
            
            result = agent.invoke("テスト企業の総資産を教えてください")
            
            assert result is not None
            assert "final_answer" in result
            assert result["final_answer"] is not None
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    def test_agent_invoke_error_handling(self):
        """エージェントエラーハンドリングテスト"""
        agent = create_agent(enable_memory=False)
        
        # LLMエラーのシミュレーション
        with patch('langchain_openai.ChatOpenAI.invoke', side_effect=Exception("LLMエラー")):
            result = agent.invoke("テスト質問")
            
            assert result is not None
            assert "error_message" in result
            assert "final_answer" in result
            assert "エラーが発生しました" in result["final_answer"]
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    def test_agent_stream(self):
        """ストリーミング実行テスト"""
        agent = create_agent(enable_memory=False)
        
        with patch.object(agent.app, 'stream') as mock_stream:
            mock_stream.return_value = [
                {"query_analyzer": {"query": "テスト質問"}},
                {"answer_generator": {"final_answer": "テスト回答"}}
            ]
            
            chunks = list(agent.stream("テスト質問"))
            
            assert len(chunks) > 0
            assert mock_stream.called
    
    def test_create_initial_state(self):
        """初期状態作成テスト"""
        query = "テスト質問"
        state = create_initial_state(query)
        
        assert state["query"] == query
        assert state["messages"] == []
        assert state["company_name"] is None
        assert state["search_date"] is None
        assert state["retry_count"] == 0
        assert state["tool_calls"] == []


class TestEdinetAgentNodes:
    """エージェントノードのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_llm = MagicMock()
        self.nodes = EdinetAgentNodes(self.mock_llm)
    
    def test_query_analyzer_node_success(self):
        """質問解析ノード成功テスト"""
        state = create_initial_state("楽天の総資産を教えてください")
        
        # LLMレスポンスのモック
        self.mock_llm.invoke.return_value = MagicMock(
            content='{"company_name": "楽天", "search_date": "2024-07-10", "document_type": "有価証券報告書", "analysis_type": "financial"}'
        )
        
        result = self.nodes.query_analyzer_node(state)
        
        assert result["company_name"] == "楽天"
        assert result["search_date"] == "2024-07-10"
        assert result["document_type"] == "有価証券報告書"
        assert result["analysis_type"] == "financial"
        assert result["next_action"] == "edinet_search"
    
    def test_query_analyzer_node_json_error(self):
        """質問解析ノードJSONエラーテスト"""
        state = create_initial_state("無効な質問")
        
        # 無効なJSONレスポンス
        self.mock_llm.invoke.return_value = MagicMock(content="無効なJSONレスポンス")
        
        result = self.nodes.query_analyzer_node(state)
        
        assert result["error_message"] is not None
        assert "JSON" in result["error_message"]
        assert result["next_action"] == "error_handler"
    
    @patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi')
    def test_edinet_search_node_success(self, mock_api_class):
        """EDINET検索ノード成功テスト"""
        state = create_initial_state("テスト質問")
        state["company_name"] = "テスト企業"
        state["search_date"] = "2024-07-10"
        state["document_type"] = "有価証券報告書"
        
        # 検索結果のモック
        mock_api = MagicMock()
        mock_api.get_documents_list.return_value = {
            "results": [{
                "docID": "S100TEST",
                "filerName": "テスト企業",
                "docDescription": "有価証券報告書"
            }]
        }
        mock_api_class.return_value = mock_api
        
        # SearchToolのレスポンスをモック
        with patch.object(self.nodes.search_tool, '_run') as mock_search:
            mock_search.return_value = json.dumps({
                "success": True,
                "documents": [{
                    "docID": "S100TEST",
                    "filerName": "テスト企業",
                    "docDescription": "有価証券報告書"
                }]
            })
            
            result = self.nodes.edinet_search_node(state)
            
            assert result["search_results"] is not None
            assert len(result["search_results"]) == 1
            assert result["next_action"] == "document_download"
    
    def test_edinet_search_node_no_company(self):
        """EDINET検索ノード企業名なしテスト"""
        state = create_initial_state("テスト質問")
        # company_nameを設定しない
        
        result = self.nodes.edinet_search_node(state)
        
        assert result["error_message"] is not None
        assert "企業名が指定されていません" in result["error_message"]
        assert result["next_action"] == "error_handler"
    
    def test_error_handler_node_max_retries(self):
        """エラーハンドラーノード最大リトライテスト"""
        state = create_initial_state("テスト質問")
        state["error_message"] = "テストエラー"
        state["retry_count"] = 3  # 最大リトライ数に達している
        
        result = self.nodes.error_handler_node(state)
        
        assert result["final_answer"] is not None
        assert "エラーが発生しました" in result["final_answer"]
        assert result["next_action"] == "completed"
    
    def test_no_documents_found_node(self):
        """書類未発見ノードテスト"""
        state = create_initial_state("テスト質問")
        state["company_name"] = "テスト企業"
        state["search_date"] = "2024-07-10"
        state["document_type"] = "有価証券報告書"
        
        result = self.nodes.no_documents_found_node(state)
        
        assert result["final_answer"] is not None
        assert "見つかりませんでした" in result["final_answer"]
        assert result["next_action"] == "completed"


class TestEdinetAgentState:
    """エージェント状態のテストクラス"""
    
    def test_create_initial_state(self):
        """初期状態作成テスト"""
        query = "テスト質問"
        state = create_initial_state(query)
        
        assert state["query"] == query
        assert state["messages"] == []
        assert state["company_name"] is None
        assert state["search_date"] is None
        assert state["document_type"] is None
        assert state["analysis_type"] is None
        assert state["search_terms"] is None
        assert state["search_results"] is None
        assert state["downloaded_files"] is None
        assert state["xbrl_analysis"] is None
        assert state["comparison_analysis"] is None
        assert state["final_answer"] is None
        assert state["error_message"] is None
        assert state["retry_count"] == 0
        assert state["tool_calls"] == []
        assert state["execution_time"] is None
        assert state["next_action"] is None
    
    def test_update_state(self):
        """状態更新テスト"""
        from src.edinet_analyzer.state import update_state
        
        initial_state = create_initial_state("テスト質問")
        updated_state = update_state(
            initial_state,
            company_name="テスト企業",
            search_date="2024-07-10",
            retry_count=1
        )
        
        assert updated_state["company_name"] == "テスト企業"
        assert updated_state["search_date"] == "2024-07-10"
        assert updated_state["retry_count"] == 1
        assert updated_state["query"] == "テスト質問"  # 元の値は保持
    
    def test_add_tool_call(self):
        """ツール呼び出し履歴追加テスト"""
        from src.edinet_analyzer.state import add_tool_call
        
        state = create_initial_state("テスト質問")
        updated_state = add_tool_call(
            state,
            "test_tool",
            {"input": "test"},
            {"output": "result"},
            success=True
        )
        
        assert len(updated_state["tool_calls"]) == 1
        tool_call = updated_state["tool_calls"][0]
        assert tool_call["tool_name"] == "test_tool"
        assert tool_call["inputs"] == {"input": "test"}
        assert tool_call["outputs"] == {"output": "result"}
        assert tool_call["success"] is True
        assert "timestamp" in tool_call
    
    def test_has_error(self):
        """エラー状態判定テスト"""
        from src.edinet_analyzer.state import has_error
        
        normal_state = create_initial_state("テスト質問")
        error_state = create_initial_state("テスト質問")
        error_state["error_message"] = "エラーメッセージ"
        
        assert not has_error(normal_state)
        assert has_error(error_state)
    
    def test_should_retry(self):
        """リトライ判定テスト"""
        from src.edinet_analyzer.state import should_retry
        
        # エラーなし、リトライなし
        normal_state = create_initial_state("テスト質問")
        assert not should_retry(normal_state)
        
        # エラーあり、リトライ回数少ない
        retry_state = create_initial_state("テスト質問")
        retry_state["error_message"] = "エラー"
        retry_state["retry_count"] = 1
        assert should_retry(retry_state)
        
        # エラーあり、リトライ回数上限
        max_retry_state = create_initial_state("テスト質問")
        max_retry_state["error_message"] = "エラー"
        max_retry_state["retry_count"] = 3
        assert not should_retry(max_retry_state)


@pytest.mark.integration
class TestEdinetAgentIntegration:
    """エージェント統合テスト"""
    
    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY") or not os.environ.get("EDINET_API_KEY"),
        reason="API キーが設定されていません"
    )
    def test_full_agent_workflow_mock(self):
        """モック使用の完全ワークフローテスト"""
        agent = create_agent(enable_memory=False)
        
        # 全ツールをモック化
        with patch('src.edinet_analyzer.langchain_tools.edinet_search_tool.EdinetApi') as mock_api_class:
            with patch('src.edinet_analyzer.langchain_tools.xbrl_analysis_tool.EnhancedXbrlParser') as mock_parser_class:
                
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
                
                # LLMレスポンスのモック
                with patch('langchain_openai.ChatOpenAI.invoke') as mock_llm:
                    mock_llm.side_effect = [
                        MagicMock(content='{"company_name": "テスト企業", "search_date": "2024-07-10", "document_type": "有価証券報告書", "analysis_type": "financial"}'),
                        MagicMock(content="テスト企業の総資産は10億円です。詳細な財務分析をお伝えします。")
                    ]
                    
                    # エージェント実行
                    result = agent.invoke("テスト企業の財務状況を教えてください")
                    
                    # 結果検証
                    assert result is not None
                    assert result["final_answer"] is not None
                    assert "10億円" in result["final_answer"]
                    assert result.get("execution_time") is not None
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "EDINET_API_KEY": "test_edinet_key"})
    def test_agent_error_recovery(self):
        """エージェントエラー回復テスト"""
        agent = create_agent(enable_memory=False)
        
        # 複数回のエラーとリトライをシミュレート
        with patch('langchain_openai.ChatOpenAI.invoke') as mock_llm:
            # 最初は解析エラー、次に成功
            mock_llm.side_effect = [
                Exception("一時的なエラー"),  # 最初の呼び出しでエラー
                MagicMock(content="申し訳ございません。エラーが発生しました。")  # エラーハンドラーの応答
            ]
            
            result = agent.invoke("テスト質問")
            
            assert result is not None
            assert result["final_answer"] is not None
            assert "エラーが発生しました" in result["final_answer"]