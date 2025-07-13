import pytest
from typing import List, Dict, Optional, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


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


def update_state(state: EdinetAgentState, **kwargs: Any) -> EdinetAgentState:
    """状態を更新する"""
    new_state = state.copy()
    for key, value in kwargs.items():
        if key in EdinetAgentState.__annotations__:
            new_state[key] = value
    return new_state


def add_tool_call(
    state: EdinetAgentState,
    tool_name: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    success: bool = True,
    error: Optional[str] = None
) -> EdinetAgentState:
    """ツール呼び出し履歴を追加する"""
    import time
    
    tool_call = {
        "tool_name": tool_name,
        "inputs": inputs,
        "outputs": outputs,
        "success": success,
        "error": error,
        "timestamp": time.time()
    }
    
    new_state = state.copy()
    new_state["tool_calls"] = state["tool_calls"] + [tool_call]
    return new_state


def has_error(state: EdinetAgentState) -> bool:
    """エラー状態かどうかを判定する"""
    return state.get("error_message") is not None


def should_retry(state: EdinetAgentState, max_retries: int = 3) -> bool:
    """リトライすべきかどうかを判定する"""
    return (
        has_error(state) and 
        state.get("retry_count", 0) < max_retries
    )


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
        normal_state = create_initial_state("テスト質問")
        error_state = create_initial_state("テスト質問")
        error_state["error_message"] = "エラーメッセージ"
        
        assert not has_error(normal_state)
        assert has_error(error_state)
    
    def test_should_retry(self):
        """リトライ判定テスト"""
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
    
    def test_multiple_tool_calls(self):
        """複数のツール呼び出し履歴テスト"""
        state = create_initial_state("テスト質問")
        
        # 1回目のツール呼び出し
        state = add_tool_call(
            state,
            "tool1",
            {"input1": "value1"},
            {"output1": "result1"}
        )
        
        # 2回目のツール呼び出し
        state = add_tool_call(
            state,
            "tool2",
            {"input2": "value2"},
            {"output2": "result2"}
        )
        
        assert len(state["tool_calls"]) == 2
        assert state["tool_calls"][0]["tool_name"] == "tool1"
        assert state["tool_calls"][1]["tool_name"] == "tool2"
    
    def test_state_immutability(self):
        """状態の不変性テスト"""
        original_state = create_initial_state("テスト質問")
        updated_state = update_state(original_state, company_name="新しい企業")
        
        # 元の状態は変更されていない
        assert original_state["company_name"] is None
        # 新しい状態は更新されている
        assert updated_state["company_name"] == "新しい企業"
        # オブジェクトは異なる
        assert original_state is not updated_state