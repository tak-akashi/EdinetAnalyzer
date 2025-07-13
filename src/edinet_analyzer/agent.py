"""
EDINET分析エージェントのメイン実装
"""

import os
import time
from typing import Dict, Any, Optional, Iterator
from langchain_core.language_models import BaseLLM
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import EdinetAgentState, create_initial_state
from .nodes import EdinetAgentNodes
from .edges import router, should_continue


class EdinetAnalysisAgent:
    """EDINET分析エージェントのメインクラス"""
    
    def __init__(
        self, 
        llm: Optional[BaseLLM] = None,
        enable_memory: bool = True
    ):
        """
        Args:
            llm: 使用するLLM（指定しない場合はOpenAI GPT-4oを使用）
            enable_memory: メモリ機能を有効にするかどうか
        """
        self.llm = llm or self._create_default_llm()
        self.enable_memory = enable_memory
        
        # ノードの初期化
        self.nodes = EdinetAgentNodes(self.llm)
        
        # ワークフローの構築
        self.workflow = self._build_workflow()
        
        # チェックポインター（メモリ機能）
        self.checkpointer = MemorySaver() if enable_memory else None
        
        # アプリケーションのコンパイル
        self.app = self.workflow.compile(
            checkpointer=self.checkpointer,
            debug=False
        )
    
    def _create_default_llm(self) -> BaseLLM:
        """デフォルトのLLMを作成"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,
            api_key=api_key
        )
    
    def _build_workflow(self) -> StateGraph:
        """LangGraphワークフローを構築"""
        workflow = StateGraph(EdinetAgentState)
        
        # ノードの追加
        workflow.add_node("query_analyzer", self.nodes.query_analyzer_node)
        workflow.add_node("edinet_search", self.nodes.edinet_search_node)
        workflow.add_node("document_download", self.nodes.document_download_node)
        workflow.add_node("xbrl_analysis", self.nodes.xbrl_analysis_node)
        workflow.add_node("answer_generator", self.nodes.answer_generator_node)
        workflow.add_node("error_handler", self.nodes.error_handler_node)
        workflow.add_node("no_documents_found", self.nodes.no_documents_found_node)
        
        # エントリーポイントの設定
        workflow.set_entry_point("query_analyzer")
        
        # エッジの追加
        workflow.add_conditional_edges(
            "query_analyzer",
            router,
            {
                "edinet_search": "edinet_search",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "edinet_search",
            router,
            {
                "document_download": "document_download",
                "no_documents_found": "no_documents_found",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "document_download",
            router,
            {
                "xbrl_analysis": "xbrl_analysis",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "xbrl_analysis",
            router,
            {
                "answer_generator": "answer_generator",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "answer_generator",
            router,
            {
                "completed": END
            }
        )
        
        workflow.add_conditional_edges(
            "error_handler",
            router,
            {
                "completed": END
            }
        )
        
        workflow.add_conditional_edges(
            "no_documents_found",
            router,
            {
                "completed": END
            }
        )
        
        return workflow
    
    def invoke(
        self, 
        query: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        エージェントを実行する
        
        Args:
            query: ユーザーの質問
            config: LangGraphの設定（スレッドIDなど）
            
        Returns:
            実行結果
        """
        try:
            start_time = time.time()
            
            # 初期状態の作成
            initial_state = create_initial_state(query)
            
            # エージェントの実行
            result = self.app.invoke(initial_state, config=config)
            
            # 実行時間の記録
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            
            return result
            
        except Exception as e:
            # エラー時の応答
            error_state = create_initial_state(query)
            error_state.update({
                "error_message": f"エージェント実行エラー: {str(e)}",
                "final_answer": f"申し訳ございません。システムエラーが発生しました。\\n\\nエラー詳細: {str(e)}",
                "execution_time": time.time() - start_time if 'start_time' in locals() else 0
            })
            return error_state
    
    def stream(
        self, 
        query: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        エージェントをストリーミング実行する
        
        Args:
            query: ユーザーの質問
            config: LangGraphの設定
            
        Yields:
            各ステップの実行結果
        """
        try:
            # 初期状態の作成
            initial_state = create_initial_state(query)
            
            # ストリーミング実行
            for chunk in self.app.stream(initial_state, config=config):
                yield chunk
                
        except Exception as e:
            yield {
                "error": {
                    "error_message": f"ストリーミング実行エラー: {str(e)}",
                    "final_answer": f"申し訳ございません。システムエラーが発生しました。\\n\\nエラー詳細: {str(e)}"
                }
            }
    
    def validate_environment(self) -> Dict[str, bool]:
        """
        実行環境を検証する
        
        Returns:
            検証結果
        """
        validation = {
            "edinet_api_key": bool(os.environ.get("EDINET_API_KEY")),
            "openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
            "edinet_tools": all([
                self.nodes.search_tool is not None,
                self.nodes.download_tool is not None,
                self.nodes.analysis_tool is not None
            ]),
            "llm_connection": False
        }
        
        # LLM接続テスト
        try:
            test_response = self.llm.invoke([{"role": "user", "content": "test"}])
            validation["llm_connection"] = bool(test_response)
        except Exception:
            validation["llm_connection"] = False
        
        return validation
    
    def get_workflow_diagram(self) -> str:
        """
        ワークフロー図をテキストで返す
        
        Returns:
            ワークフロー図の文字列表現
        """
        return """
        EDINET分析エージェント ワークフロー
        
        [Start] → query_analyzer
                     ↓
            ┌────────────────────────┐
            ↓                        ↓
        edinet_search          error_handler
            ↓                        ↓
        ┌───────────────┐           [End]
        ↓               ↓
    document_download  no_documents_found
        ↓                        ↓
    xbrl_analysis              [End]
        ↓
    answer_generator
        ↓
      [End]
        """
    
    def get_conversation_history(
        self, 
        thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        会話履歴を取得する（メモリ機能が有効な場合）
        
        Args:
            thread_id: スレッドID
            
        Returns:
            会話履歴
        """
        if not self.checkpointer:
            return None
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            return self.checkpointer.get(config)
        except Exception:
            return None


def create_agent(
    model_name: str = "gpt-4o",
    enable_memory: bool = True,
    api_key: Optional[str] = None
) -> EdinetAnalysisAgent:
    """
    EDINET分析エージェントを作成する便利関数
    
    Args:
        model_name: 使用するモデル名
        enable_memory: メモリ機能を有効にするかどうか
        api_key: OpenAI APIキー（指定しない場合は環境変数から取得）
        
    Returns:
        EDINET分析エージェント
    """
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.1,
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    return EdinetAnalysisAgent(llm=llm, enable_memory=enable_memory)