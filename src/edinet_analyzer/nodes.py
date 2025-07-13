"""
EDINET分析エージェントのノード実装
"""

import json
import os
from datetime import date
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage

from .state import EdinetAgentState, update_state, add_tool_call
from .langchain_tools import (
    EdinetSearchTool,
    EdinetDownloadTool,
    EdinetMultiDateSearchTool,
    XbrlAnalysisTool,
    XbrlComparisonTool
)


class EdinetAgentNodes:
    """EDINET分析エージェントのノード実装"""
    
    def __init__(self, llm: BaseLLM):
        """
        Args:
            llm: 使用するLLM
        """
        self.llm = llm
        
        # ツールの初期化
        self.search_tool = None
        self.multi_search_tool = None
        self.download_tool = None
        self.analysis_tool = None
        self.comparison_tool = None
        
        try:
            self.search_tool = EdinetSearchTool()
            print("EdinetSearchTool initialized successfully")
        except Exception as e:
            print(f"Failed to initialize EdinetSearchTool: {e}")
            
        try:
            self.multi_search_tool = EdinetMultiDateSearchTool()
            print("EdinetMultiDateSearchTool initialized successfully")
        except Exception as e:
            print(f"Failed to initialize EdinetMultiDateSearchTool: {e}")
            
        try:
            self.download_tool = EdinetDownloadTool()
            print("EdinetDownloadTool initialized successfully")
        except Exception as e:
            print(f"Failed to initialize EdinetDownloadTool: {e}")
            
        try:
            self.analysis_tool = XbrlAnalysisTool()
            print("XbrlAnalysisTool initialized successfully")
        except Exception as e:
            print(f"Failed to initialize XbrlAnalysisTool: {e}")
            
        try:
            self.comparison_tool = XbrlComparisonTool()
            print("XbrlComparisonTool initialized successfully")
        except Exception as e:
            print(f"Failed to initialize XbrlComparisonTool: {e}")
    
    def query_analyzer_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """質問解析ノード"""
        try:
            query = state["query"]
            
            # LLMに質問解析を依頼（日本語文字列のエンコーディング問題を回避）
            current_date = date.today().strftime("%Y-%m-%d")
            analysis_prompt = """
            以下のユーザーの質問を分析し、JSON形式で情報を抽出してください。
            
            今日の日付: {}
            質問: {}

            以下の形式でJSONを返してください：
            {{
                "company_name": "企業名（抽出できない場合はnull）",
                "search_date": "検索対象日（指定がない場合は今日の日付 YYYY-MM-DD）",
                "document_type": "書類種別（デフォルト：有価証券報告書）",
                "analysis_type": "分析タイプ（financial/comparison/search）"
            }}
            """.format(current_date, query)
            
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            
            try:
                # JSONレスポンスをパース（マークダウンのコードブロックを除去）
                content = response.content.strip()
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()
                
                analysis_result = json.loads(content)
                
                # デフォルト値の設定（現在日付を使用）
                company_name = analysis_result.get("company_name")
                search_date = analysis_result.get("search_date", date.today().strftime("%Y-%m-%d"))
                document_type = analysis_result.get("document_type", "有価証券報告書")
                analysis_type = analysis_result.get("analysis_type", "financial")
                
                # 次のアクションを決定
                next_action = "edinet_search" if company_name else "error_handler"
                
                return update_state(
                    state,
                    company_name=company_name,
                    search_date=search_date,
                    document_type=document_type,
                    analysis_type=analysis_type,
                    next_action=next_action
                )
                
            except json.JSONDecodeError:
                return update_state(
                    state,
                    error_message=f"JSON解析エラー: {response.content[:200]}",
                    next_action="error_handler"
                )
                
        except Exception as e:
            return update_state(
                state,
                error_message=f"質問解析エラー: {str(e)}",
                next_action="error_handler"
            )
    
    def edinet_search_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """EDINET検索ノード"""
        try:
            company_name = state.get("company_name")
            if not company_name:
                return update_state(
                    state,
                    error_message="企業名が指定されていません",
                    next_action="error_handler"
                )
            
            search_date = state.get("search_date", date.today().strftime("%Y-%m-%d"))
            document_type = state.get("document_type", "有価証券報告書")
            
            if not self.multi_search_tool:
                return update_state(
                    state,
                    error_message="複数日付検索ツールが初期化されていません",
                    next_action="error_handler"
                )
            
            # 複数日付遡及検索を実行
            search_result = self.multi_search_tool._run(
                company_name=company_name,
                document_type=document_type,
                max_days_back=90,
                priority_days=[7, 30, 90]
            )
            
            try:
                result_data = json.loads(search_result)
                
                if result_data.get("success") and result_data.get("all_documents"):
                    # 検索成功 - 最新の書類を使用
                    return update_state(
                        state,
                        search_results=result_data["all_documents"],
                        search_date=result_data.get("latest_document", {}).get("search_date", search_date),
                        next_action="document_download"
                    )
                else:
                    # 複数日付検索で見つからない場合、従来の単一日付検索にフォールバック
                    if self.search_tool:
                        fallback_result = self.search_tool._run(
                            company_name=company_name,
                            date=search_date,
                            document_type=document_type
                        )
                        fallback_data = json.loads(fallback_result)
                        
                        if fallback_data.get("success") and fallback_data.get("documents"):
                            return update_state(
                                state,
                                search_results=fallback_data["documents"],
                                next_action="document_download"
                            )
                    
                    return update_state(
                        state,
                        error_message=f"企業「{company_name}」の{document_type}が見つかりませんでした",
                        next_action="error_handler"
                    )
                    
            except json.JSONDecodeError:
                return update_state(
                    state,
                    error_message=f"検索結果の解析に失敗しました: {search_result[:200]}",
                    next_action="error_handler"
                )
                
        except Exception as e:
            return update_state(
                state,
                error_message=f"検索エラー: {str(e)}",
                next_action="error_handler"
            )
    
    def document_download_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """書類ダウンロードノード"""
        try:
            search_results = state.get("search_results", [])
            if not search_results:
                return update_state(
                    state,
                    error_message="ダウンロード対象の書類がありません",
                    next_action="error_handler"
                )
            
            if not self.download_tool:
                return update_state(
                    state,
                    error_message="ダウンロードツールが初期化されていません",
                    next_action="error_handler"
                )
            
            downloaded_files = []
            
            # 最初の書類をダウンロード
            doc = search_results[0]
            doc_id = doc.get("docID")
            
            if doc_id:
                download_result = self.download_tool._run(doc_id, "xbrl")
                
                try:
                    result_data = json.loads(download_result)
                    if result_data.get("success"):
                        downloaded_files.append(result_data.get("file_path"))
                except json.JSONDecodeError:
                    pass
            
            if downloaded_files:
                return update_state(
                    state,
                    downloaded_files=downloaded_files,
                    next_action="xbrl_analysis"
                )
            else:
                return update_state(
                    state,
                    error_message="書類のダウンロードに失敗しました",
                    next_action="error_handler"
                )
                
        except Exception as e:
            return update_state(
                state,
                error_message=f"ダウンロードエラー: {str(e)}",
                next_action="error_handler"
            )
    
    def xbrl_analysis_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """XBRL解析ノード"""
        try:
            downloaded_files = state.get("downloaded_files", [])
            if not downloaded_files:
                return update_state(
                    state,
                    error_message="解析対象のファイルがありません",
                    next_action="error_handler"
                )
            
            if not self.analysis_tool:
                return update_state(
                    state,
                    error_message="解析ツールが初期化されていません",
                    next_action="error_handler"
                )
            
            analysis_type = state.get("analysis_type", "financial")
            search_terms = state.get("search_terms")
            
            # XBRL解析実行
            file_path = downloaded_files[0]
            analysis_result = self.analysis_tool._run(
                file_path=file_path,
                analysis_type=analysis_type,
                search_terms=search_terms
            )
            
            try:
                result_data = json.loads(analysis_result)
                
                if result_data.get("success"):
                    return update_state(
                        state,
                        xbrl_analysis=result_data,
                        next_action="answer_generator"
                    )
                else:
                    return update_state(
                        state,
                        error_message=f"XBRL解析に失敗しました: {result_data.get('message', 'Unknown error')}",
                        next_action="error_handler"
                    )
                    
            except json.JSONDecodeError:
                return update_state(
                    state,
                    error_message=f"解析結果の解析に失敗しました: {analysis_result[:200]}",
                    next_action="error_handler"
                )
                
        except Exception as e:
            return update_state(
                state,
                error_message=f"XBRL解析エラー: {str(e)}",
                next_action="error_handler"
            )
    
    def answer_generator_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """回答生成ノード"""
        try:
            query = state["query"]
            company_name = state.get("company_name", "企業")
            xbrl_analysis = state.get("xbrl_analysis", {})
            
            if not xbrl_analysis:
                return update_state(
                    state,
                    error_message="解析結果がありません",
                    next_action="error_handler"
                )
            
            # LLMに回答生成を依頼
            answer_prompt = f"""
            ユーザーの質問に対して、XBRL解析結果を基に分かりやすい回答を生成してください。

            質問: {query}
            企業名: {company_name}
            解析結果: {json.dumps(xbrl_analysis, ensure_ascii=False, indent=2)}

            以下の点を考慮して回答してください：
            1. 財務データを具体的な数値とともに説明する
            2. 専門用語は分かりやすく説明する
            3. 日本語で自然な回答にする
            4. 解析結果の信頼性についても言及する

            回答:
            """
            
            response = self.llm.invoke([HumanMessage(content=answer_prompt)])
            
            return update_state(
                state,
                final_answer=response.content,
                next_action="completed"
            )
            
        except Exception as e:
            return update_state(
                state,
                error_message=f"回答生成エラー: {str(e)}",
                next_action="error_handler"
            )
    
    def error_handler_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """エラーハンドラーノード"""
        error_message = state.get("error_message", "不明なエラーが発生しました")
        retry_count = state.get("retry_count", 0)
        
        if retry_count >= 3:
            # 最大リトライ数に達した場合
            final_answer = f"""
            申し訳ございません。処理中にエラーが発生しました。

            エラー詳細: {error_message}

            以下をご確認ください：
            1. 企業名が正確に入力されているか
            2. 指定した日付に該当する書類が存在するか
            3. ネットワーク接続が正常か

            しばらく時間をおいてから再度お試しください。
            """
        else:
            # リトライ可能な場合
            final_answer = f"""
            処理中にエラーが発生しましたが、再試行いたします。

            エラー詳細: {error_message}
            """
        
        return update_state(
            state,
            final_answer=final_answer.strip(),
            next_action="completed"
        )
    
    def no_documents_found_node(self, state: EdinetAgentState) -> EdinetAgentState:
        """書類未発見ノード"""
        company_name = state.get("company_name", "指定した企業")
        search_date = state.get("search_date", "指定した日付")
        document_type = state.get("document_type", "有価証券報告書")
        
        final_answer = f"""
        申し訳ございません。{company_name}の{document_type}が見つかりませんでした。

        検索条件:
        - 企業名: {company_name}
        - 日付: {search_date}
        - 書類種別: {document_type}

        以下をご確認ください：
        1. 企業名の表記が正確か（正式な企業名で検索してください）
        2. 指定した日付に書類が提出されているか
        3. 書類種別が適切か

        別の条件で再度検索をお試しください。
        """
        
        return update_state(
            state,
            final_answer=final_answer.strip(),
            next_action="completed"
        )