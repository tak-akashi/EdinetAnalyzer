"""
EDINET分析エージェントのエッジ（ルーティング）実装
"""

from typing import Literal
from .state import EdinetAgentState


def router(state: EdinetAgentState) -> Literal[
    "edinet_search", "document_download", "xbrl_analysis", 
    "answer_generator", "error_handler", "no_documents_found", "completed"
]:
    """
    現在の状態に基づいて次のノードを決定する
    
    Args:
        state: 現在のエージェント状態
        
    Returns:
        次に実行するノードの名前
    """
    next_action = state.get("next_action")
    
    if next_action == "edinet_search":
        return "edinet_search"
    elif next_action == "document_download":
        return "document_download"
    elif next_action == "xbrl_analysis":
        return "xbrl_analysis"
    elif next_action == "answer_generator":
        return "answer_generator"
    elif next_action == "error_handler":
        return "error_handler"
    elif next_action == "no_documents_found":
        return "no_documents_found"
    elif next_action == "completed":
        return "completed"
    else:
        # デフォルトはエラーハンドラー
        return "error_handler"


def should_continue(state: EdinetAgentState) -> Literal["continue", "end"]:
    """
    ワークフローを継続するかどうかを決定する
    
    Args:
        state: 現在のエージェント状態
        
    Returns:
        "continue": ワークフローを継続
        "end": ワークフローを終了
    """
    next_action = state.get("next_action")
    
    if next_action == "completed":
        return "end"
    else:
        return "continue"


def get_next_node(state: EdinetAgentState) -> str:
    """
    次のノード名を取得する（デバッグ用）
    
    Args:
        state: 現在のエージェント状態
        
    Returns:
        次のノード名
    """
    return router(state)


def validate_state_transition(
    current_state: EdinetAgentState, 
    next_node: str
) -> bool:
    """
    状態遷移が有効かどうかを検証する
    
    Args:
        current_state: 現在の状態
        next_node: 次のノード名
        
    Returns:
        遷移が有効な場合True、無効な場合False
    """
    valid_transitions = {
        "query_analyzer": ["edinet_search", "error_handler"],
        "edinet_search": ["document_download", "no_documents_found", "error_handler"],
        "document_download": ["xbrl_analysis", "error_handler"],
        "xbrl_analysis": ["answer_generator", "error_handler"],
        "answer_generator": ["completed", "error_handler"],
        "error_handler": ["completed", "edinet_search"],  # リトライ可能
        "no_documents_found": ["completed"]
    }
    
    current_action = current_state.get("next_action")
    
    # 現在のアクションが定義されていない場合は無効
    if not current_action:
        return False
    
    # 有効な遷移リストに含まれているかチェック
    return next_node in valid_transitions.get(current_action, [])


def get_workflow_status(state: EdinetAgentState) -> dict:
    """
    ワークフローの現在のステータスを取得する
    
    Args:
        state: 現在のエージェント状態
        
    Returns:
        ステータス情報の辞書
    """
    next_action = state.get("next_action")
    error_message = state.get("error_message")
    retry_count = state.get("retry_count", 0)
    
    status = {
        "current_step": next_action,
        "is_completed": next_action == "completed",
        "has_error": error_message is not None,
        "retry_count": retry_count,
        "progress_percentage": _calculate_progress(next_action)
    }
    
    if error_message:
        status["error_message"] = error_message
    
    return status


def _calculate_progress(next_action: str) -> int:
    """
    現在のアクションに基づいて進捗パーセンテージを計算する
    
    Args:
        next_action: 次のアクション
        
    Returns:
        進捗パーセンテージ（0-100）
    """
    progress_map = {
        "edinet_search": 20,
        "document_download": 40,
        "xbrl_analysis": 60,
        "answer_generator": 80,
        "completed": 100,
        "error_handler": 0,
        "no_documents_found": 100
    }
    
    return progress_map.get(next_action, 0)