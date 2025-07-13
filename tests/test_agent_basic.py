import pytest
import json
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


# テスト用の最小限の状態定義
class EdinetAgentState(TypedDict):
    """テスト用のエージェント状態"""
    messages: List[BaseMessage]
    query: str
    company_name: Optional[str]
    search_date: Optional[str]
    document_type: Optional[str]
    analysis_type: Optional[str]
    search_terms: Optional[List[str]]
    search_results: Optional[List[Dict[str, Any]]]
    downloaded_files: Optional[List[str]]
    xbrl_analysis: Optional[Dict[str, Any]]
    comparison_analysis: Optional[Dict[str, Any]]
    final_answer: Optional[str]
    error_message: Optional[str]
    retry_count: int
    tool_calls: List[Dict[str, Any]]
    execution_time: Optional[float]
    next_action: Optional[str]


def create_initial_state(query: str) -> EdinetAgentState:
    """初期状態を作成する"""
    return EdinetAgentState(
        messages=[],
        query=query,
        company_name=None,
        search_date=None,
        document_type=None,
        analysis_type=None,
        search_terms=None,
        search_results=None,
        downloaded_files=None,
        xbrl_analysis=None,
        comparison_analysis=None,
        final_answer=None,
        error_message=None,
        retry_count=0,
        tool_calls=[],
        execution_time=None,
        next_action=None
    )


# テスト用のモックノードクラス
class MockEdinetAgentNodes:
    """テスト用のモックノード"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def query_analyzer_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """質問解析ノード（モック）"""
        try:
            # 簡単なルールベースで企業名を抽出
            query = state["query"]
            company_name = None
            
            if "楽天" in query:
                company_name = "楽天"
            elif "ソフトバンク" in query:
                company_name = "ソフトバンク"
            elif "トヨタ" in query:
                company_name = "トヨタ自動車"
            
            new_state = state.copy()
            new_state.update({
                "company_name": company_name,
                "search_date": "2024-07-10",
                "document_type": "有価証券報告書",
                "analysis_type": "financial",
                "next_action": "edinet_search" if company_name else "error_handler"
            })
            
            return new_state
        except Exception as e:
            new_state = state.copy()
            new_state.update({
                "error_message": f"質問解析エラー: {str(e)}",
                "next_action": "error_handler"
            })
            return new_state
    
    def edinet_search_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """EDINET検索ノード（モック）"""
        try:
            company_name = state["company_name"]
            if not company_name:
                new_state = state.copy()
                new_state.update({
                    "error_message": "企業名が指定されていません",
                    "next_action": "error_handler"
                })
                return new_state
            
            # モック検索結果
            mock_results = [{
                "docID": "S100TEST",
                "filerName": company_name,
                "docDescription": "有価証券報告書",
                "xbrlFlag": "1"
            }]
            
            new_state = state.copy()
            new_state.update({
                "search_results": mock_results,
                "next_action": "document_download"
            })
            
            return new_state
        except Exception as e:
            new_state = state.copy()
            new_state.update({
                "error_message": f"検索エラー: {str(e)}",
                "next_action": "error_handler"
            })
            return new_state
    
    def document_download_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """書類ダウンロードノード（モック）"""
        try:
            search_results = state.get("search_results", [])
            if not search_results:
                new_state = state.copy()
                new_state.update({
                    "error_message": "ダウンロード対象の書類がありません",
                    "next_action": "error_handler"
                })
                return new_state
            
            # モックダウンロード結果
            downloaded_files = [f"temp_downloads/{search_results[0]['docID']}_xbrl.zip"]
            
            new_state = state.copy()
            new_state.update({
                "downloaded_files": downloaded_files,
                "next_action": "xbrl_analysis"
            })
            
            return new_state
        except Exception as e:
            new_state = state.copy()
            new_state.update({
                "error_message": f"ダウンロードエラー: {str(e)}",
                "next_action": "error_handler"
            })
            return new_state
    
    def xbrl_analysis_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """XBRL解析ノード（モック）"""
        try:
            downloaded_files = state.get("downloaded_files", [])
            if not downloaded_files:
                new_state = state.copy()
                new_state.update({
                    "error_message": "解析対象のファイルがありません",
                    "next_action": "error_handler"
                })
                return new_state
            
            # モック解析結果
            mock_analysis = {
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
            
            new_state = state.copy()
            new_state.update({
                "xbrl_analysis": mock_analysis,
                "next_action": "answer_generator"
            })
            
            return new_state
        except Exception as e:
            new_state = state.copy()
            new_state.update({
                "error_message": f"解析エラー: {str(e)}",
                "next_action": "error_handler"
            })
            return new_state
    
    def answer_generator_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """回答生成ノード（モック）"""
        try:
            query = state["query"]
            company_name = state.get("company_name", "企業")
            xbrl_analysis = state.get("xbrl_analysis", {})
            
            if not xbrl_analysis:
                new_state = state.copy()
                new_state.update({
                    "error_message": "解析結果がありません",
                    "next_action": "error_handler"
                })
                return new_state
            
            # モック回答生成
            financial_data = xbrl_analysis.get("financial_data", {})
            total_assets = financial_data.get("total_assets", {})
            
            final_answer = f"""
            {company_name}の財務分析結果をお伝えします。

            【主要財務データ】
            - {total_assets.get('display_name', '総資産')}: {total_assets.get('formatted_value', 'データなし')}

            この分析は最新のXBRLデータに基づいています。
            """
            
            new_state = state.copy()
            new_state.update({
                "final_answer": final_answer.strip(),
                "next_action": "completed"
            })
            
            return new_state
        except Exception as e:
            new_state = state.copy()
            new_state.update({
                "error_message": f"回答生成エラー: {str(e)}",
                "next_action": "error_handler"
            })
            return new_state
    
    def error_handler_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """エラーハンドラーノード（モック）"""
        error_message = state.get("error_message", "不明なエラーが発生しました")
        retry_count = state.get("retry_count", 0)
        
        if retry_count >= 3:
            final_answer = f"申し訳ございません。処理中にエラーが発生しました。\n\nエラー詳細: {error_message}"
            new_state = state.copy()
            new_state.update({
                "final_answer": final_answer,
                "next_action": "completed"
            })
            return new_state
        
        new_state = state.copy()
        new_state.update({
            "final_answer": f"エラーが発生しました: {error_message}",
            "next_action": "completed"
        })
        return new_state


# テスト用のモックエージェント
class MockEdinetAnalysisAgent:
    """テスト用のモックエージェント"""
    
    def __init__(self):
        self.llm = MagicMock()
        self.nodes = MockEdinetAgentNodes(self.llm)
    
    def invoke(self, query: str) -> Dict[str, Any]:
        """エージェント実行（モック）"""
        try:
            import time
            start_time = time.time()
            
            # 初期状態作成
            state = create_initial_state(query)
            
            # ワークフロー実行
            state = self.nodes.query_analyzer_node(state)
            
            if state.get("next_action") == "edinet_search":
                state = self.nodes.edinet_search_node(state)
            
            if state.get("next_action") == "document_download":
                state = self.nodes.document_download_node(state)
            
            if state.get("next_action") == "xbrl_analysis":
                state = self.nodes.xbrl_analysis_node(state)
            
            if state.get("next_action") == "answer_generator":
                state = self.nodes.answer_generator_node(state)
            
            if state.get("next_action") == "error_handler":
                state = self.nodes.error_handler_node(state)
            
            # 実行時間記録
            execution_time = time.time() - start_time
            state["execution_time"] = execution_time
            
            return state
            
        except Exception as e:
            error_state = create_initial_state(query)
            error_state.update({
                "error_message": f"エージェント実行エラー: {str(e)}",
                "final_answer": f"申し訳ございません。システムエラーが発生しました。\n\nエラー詳細: {str(e)}"
            })
            return error_state


class TestBasicAgentFunctionality:
    """基本的なエージェント機能のテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.agent = MockEdinetAnalysisAgent()
    
    def test_agent_initialization(self):
        """エージェントの初期化テスト"""
        assert self.agent is not None
        assert self.agent.llm is not None
        assert self.agent.nodes is not None
    
    def test_successful_query_processing(self):
        """正常な質問処理テスト"""
        result = self.agent.invoke("楽天の総資産を教えてください")
        
        assert result is not None
        assert result["query"] == "楽天の総資産を教えてください"
        assert result["company_name"] == "楽天"
        assert result["final_answer"] is not None
        assert "10億円" in result["final_answer"]
        assert result.get("execution_time") is not None
    
    def test_company_name_extraction(self):
        """企業名抽出テスト"""
        test_cases = [
            ("楽天グループの財務状況を教えて", "楽天"),
            ("ソフトバンクの業績は？", "ソフトバンク"),
            ("トヨタ自動車の売上を知りたい", "トヨタ自動車"),
        ]
        
        for query, expected_company in test_cases:
            result = self.agent.invoke(query)
            assert result["company_name"] == expected_company
            assert result["final_answer"] is not None
    
    def test_unknown_company_handling(self):
        """未知の企業に対するハンドリングテスト"""
        result = self.agent.invoke("未知の企業の財務状況を教えて")
        
        assert result["company_name"] is None
        # company_nameがNoneの場合、error_handlerに進むため最終的にfinal_answerにエラーが含まれる
        assert result["final_answer"] is not None
        assert "エラー" in result["final_answer"]
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # エラーを意図的に発生させるテスト
        state = create_initial_state("テスト質問")
        state["error_message"] = "テストエラー"
        
        result = self.agent.nodes.error_handler_node(state)
        
        assert result["final_answer"] is not None
        assert "エラーが発生しました" in result["final_answer"]
        assert result["next_action"] == "completed"
    
    def test_workflow_progression(self):
        """ワークフローの進行テスト"""
        query = "楽天の財務データを分析してください"
        result = self.agent.invoke(query)
        
        # ワークフローの各ステップが正しく実行されたことを確認
        assert result["company_name"] is not None
        assert result["search_results"] is not None
        assert result["downloaded_files"] is not None
        assert result["xbrl_analysis"] is not None
        assert result["final_answer"] is not None
    
    def test_analysis_type_detection(self):
        """分析タイプ検出テスト"""
        result = self.agent.invoke("楽天の財務状況を分析して")
        
        assert result["analysis_type"] == "financial"
        assert result["document_type"] == "有価証券報告書"
        assert result["search_date"] == "2024-07-10"
    
    def test_empty_query_handling(self):
        """空の質問に対するハンドリング"""
        result = self.agent.invoke("")
        
        # 空の質問でもエラーハンドリングされること
        assert result is not None
        assert result["query"] == ""
        # 企業名が抽出できないためエラーになる
        assert result["company_name"] is None
    
    def test_japanese_text_handling(self):
        """日本語テキストの処理テスト"""
        japanese_queries = [
            "楽天グループ株式会社の最新の有価証券報告書から総資産額を教えてください",
            "ソフトバンクグループの純利益について詳しく知りたいです",
            "トヨタ自動車の財務状況を分析してください"
        ]
        
        for query in japanese_queries:
            result = self.agent.invoke(query)
            assert result is not None
            assert result["final_answer"] is not None
            assert len(result["final_answer"]) > 0


class TestAgentNodes:
    """エージェントノードのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_llm = MagicMock()
        self.nodes = MockEdinetAgentNodes(self.mock_llm)
    
    def test_query_analyzer_node(self):
        """質問解析ノードのテスト"""
        state = create_initial_state("楽天の総資産を教えてください")
        result = self.nodes.query_analyzer_node(state)
        
        assert result["company_name"] == "楽天"
        assert result["search_date"] == "2024-07-10"
        assert result["document_type"] == "有価証券報告書"
        assert result["analysis_type"] == "financial"
        assert result["next_action"] == "edinet_search"
    
    def test_edinet_search_node(self):
        """EDINET検索ノードのテスト"""
        state = create_initial_state("テスト質問")
        state["company_name"] = "テスト企業"
        
        result = self.nodes.edinet_search_node(state)
        
        assert result["search_results"] is not None
        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["filerName"] == "テスト企業"
        assert result["next_action"] == "document_download"
    
    def test_document_download_node(self):
        """書類ダウンロードノードのテスト"""
        state = create_initial_state("テスト質問")
        state["search_results"] = [{
            "docID": "S100TEST",
            "filerName": "テスト企業",
            "docDescription": "有価証券報告書"
        }]
        
        result = self.nodes.document_download_node(state)
        
        assert result["downloaded_files"] is not None
        assert len(result["downloaded_files"]) == 1
        assert "S100TEST_xbrl.zip" in result["downloaded_files"][0]
        assert result["next_action"] == "xbrl_analysis"
    
    def test_xbrl_analysis_node(self):
        """XBRL解析ノードのテスト"""
        state = create_initial_state("テスト質問")
        state["downloaded_files"] = ["temp_downloads/S100TEST_xbrl.zip"]
        
        result = self.nodes.xbrl_analysis_node(state)
        
        assert result["xbrl_analysis"] is not None
        assert "financial_data" in result["xbrl_analysis"]
        assert result["next_action"] == "answer_generator"
    
    def test_answer_generator_node(self):
        """回答生成ノードのテスト"""
        state = create_initial_state("楽天の総資産を教えて")
        state["company_name"] = "楽天"
        state["xbrl_analysis"] = {
            "financial_data": {
                "total_assets": {
                    "value": 1000000000,
                    "formatted_value": "10億円",
                    "display_name": "総資産"
                }
            }
        }
        
        result = self.nodes.answer_generator_node(state)
        
        assert result["final_answer"] is not None
        assert "楽天" in result["final_answer"]
        assert "10億円" in result["final_answer"]
        assert result["next_action"] == "completed"