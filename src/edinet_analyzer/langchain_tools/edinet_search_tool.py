from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any, Optional
import json
from datetime import datetime, timedelta
from ..tools.edinet_api import EdinetApi


class EdinetSearchInput(BaseModel):
    """EDINET検索ツールの入力スキーマ"""
    company_name: str = Field(description="検索対象の企業名")
    date: Optional[str] = Field(None, description="検索対象の日付 (YYYY-MM-DD形式、省略時は前日)")
    document_type: Optional[str] = Field("有価証券報告書", description="取得する書類種別")


class EdinetSearchTool(BaseTool):
    """
    EDINET APIを使って企業の開示書類を検索するLangChainツール
    """
    name: str = "edinet_search"
    description: str = """EDINET APIを使用して企業の開示書類を検索します。企業名を指定すると、関連する開示書類のリストと書類IDを取得できます。特定の日付や書類種別でフィルタリングも可能です。"""
    args_schema: Type[BaseModel] = EdinetSearchInput
    
    def __init__(self):
        super().__init__()
        # Pydantic v2対応: 属性の動的設定
        object.__setattr__(self, 'edinet_api', EdinetApi())
    
    def _run(self, company_name: str, date: Optional[str] = None, 
             document_type: Optional[str] = "有価証券報告書") -> str:
        """
        EDINET APIで企業の書類を検索する
        
        Args:
            company_name: 検索対象の企業名
            date: 検索対象の日付 (YYYY-MM-DD)
            document_type: 書類種別
            
        Returns:
            str: 検索結果のJSON文字列
        """
        try:
            # 日付が指定されていない場合は前日を使用
            if date is None:
                search_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                search_date = date
            
            # EDINET APIで書類一覧を取得
            documents_response = self.edinet_api.get_documents_list(date=search_date)
            
            if not documents_response or 'results' not in documents_response:
                return json.dumps({
                    "success": False,
                    "message": f"日付 {search_date} の書類一覧の取得に失敗しました",
                    "documents": []
                }, ensure_ascii=False, indent=2)
            
            # 企業名で書類をフィルタリング
            filtered_documents = []
            for doc in documents_response['results']:
                doc_description = doc.get('docDescription', '') or ''
                submitter_name = doc.get('filerName', '') or ''
                
                # 企業名が含まれているかチェック
                if (company_name in submitter_name or 
                    company_name in doc_description):
                    
                    # 書類種別でフィルタリング（document_typeが指定されていない場合は全て含める）
                    if not document_type or document_type in doc_description:
                        filtered_documents.append({
                            'docID': doc.get('docID'),
                            'filerName': submitter_name,
                            'docDescription': doc_description,
                            'submitDateTime': doc.get('submitDateTime'),
                            'docInfoEditStatus': doc.get('docInfoEditStatus'),
                            'disclosureStatus': doc.get('disclosureStatus'),
                            'xbrlFlag': doc.get('xbrlFlag'),
                            'pdfFlag': doc.get('pdfFlag')
                        })
            
            result = {
                "success": True,
                "company_name": company_name,
                "search_date": search_date,
                "document_type": document_type,
                "total_found": len(filtered_documents),
                "documents": filtered_documents
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"EDINET検索中にエラーが発生しました: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    async def _arun(self, company_name: str, date: Optional[str] = None,
                    document_type: Optional[str] = "有価証券報告書") -> str:
        """非同期実行版"""
        return self._run(company_name, date, document_type)


class EdinetDownloadInput(BaseModel):
    """EDINET書類ダウンロードツールの入力スキーマ"""
    doc_id: str = Field(description="ダウンロードする書類のdocID")
    document_type: str = Field("xbrl", description="ダウンロードする書類タイプ (xbrl または main)")


class EdinetDownloadTool(BaseTool):
    """
    EDINET APIを使って書類をダウンロードするLangChainツール
    """
    name: str = "edinet_download"
    description: str = """EDINET APIを使用して指定されたdocIDの書類をダウンロードします。XBRLファイルまたはメイン書類（PDF等）をダウンロードできます。"""
    args_schema: Type[BaseModel] = EdinetDownloadInput
    
    def __init__(self):
        super().__init__()
        # Pydantic v2対応: 属性の動的設定
        object.__setattr__(self, 'edinet_api', EdinetApi())
    
    def _run(self, doc_id: str, document_type: str = "xbrl") -> str:
        """
        EDINET APIで書類をダウンロードする
        
        Args:
            doc_id: 書類のdocID
            document_type: ダウンロードタイプ ("xbrl" または "main")
            
        Returns:
            str: ダウンロード結果のJSON文字列
        """
        try:
            if document_type.lower() == "xbrl":
                file_path = self.edinet_api.download_xbrl_document(doc_id)
            else:
                file_path = self.edinet_api.download_main_document(doc_id)
            
            if file_path:
                result = {
                    "success": True,
                    "doc_id": doc_id,
                    "document_type": document_type,
                    "file_path": file_path,
                    "message": f"書類のダウンロードが完了しました: {file_path}"
                }
            else:
                result = {
                    "success": False,
                    "doc_id": doc_id,
                    "document_type": document_type,
                    "message": "書類のダウンロードに失敗しました"
                }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"ダウンロード中にエラーが発生しました: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    async def _arun(self, doc_id: str, document_type: str = "xbrl") -> str:
        """非同期実行版"""
        return self._run(doc_id, document_type)


if __name__ == "__main__":
    # テスト実行用のコード
    search_tool = EdinetSearchTool()
    download_tool = EdinetDownloadTool()
    
    # 検索テスト
    print("=== EDINET検索テスト ===")
    search_result = search_tool._run("楽天", date="2024-07-10")
    print(search_result)
    
    # ダウンロードテスト（実際のdocIDが必要）
    # download_result = download_tool._run("S100XXXX", "xbrl")
    # print(download_result)