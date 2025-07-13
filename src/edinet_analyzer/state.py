"""
EDINET分析エージェントの状態管理モジュール
"""

from typing import List, Dict, Optional, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
import time


class EdinetAgentState(TypedDict):
    """EDINET分析エージェントの状態"""
    messages: List[BaseMessage]           # 会話履歴
    query: str                           # ユーザー質問
    company_name: Optional[str]          # 企業名
    search_date: Optional[str]           # 検索日
    document_type: Optional[str]         # 書類種別
    analysis_type: Optional[str]         # 分析タイプ
    search_terms: Optional[List[str]]    # 検索キーワード
    search_results: Optional[List[Dict[str, Any]]]  # 検索結果
    downloaded_files: Optional[List[str]] # ダウンロードファイル
    xbrl_analysis: Optional[Dict[str, Any]]  # XBRL解析結果
    comparison_analysis: Optional[Dict[str, Any]]  # 比較分析結果
    final_answer: Optional[str]          # 最終回答
    error_message: Optional[str]         # エラーメッセージ
    retry_count: int                     # リトライ回数
    tool_calls: List[Dict[str, Any]]     # ツール呼び出し履歴
    execution_time: Optional[float]      # 実行時間
    next_action: Optional[str]           # 次アクション


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


def increment_retry_count(state: EdinetAgentState) -> EdinetAgentState:
    """リトライ回数を増加させる"""
    new_state = state.copy()
    new_state["retry_count"] = state.get("retry_count", 0) + 1
    return new_state


def clear_error(state: EdinetAgentState) -> EdinetAgentState:
    """エラー状態をクリアする"""
    new_state = state.copy()
    new_state["error_message"] = None
    return new_state


def set_next_action(state: EdinetAgentState, action: str) -> EdinetAgentState:
    """次のアクションを設定する"""
    new_state = state.copy()
    new_state["next_action"] = action
    return new_state