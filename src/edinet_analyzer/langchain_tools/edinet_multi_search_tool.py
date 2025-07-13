"""
EDINET複数日付遡及検索ツール

企業名を指定して複数の日付を遡って検索し、
最新の開示書類を効率的に見つけるためのツール
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from ..tools.edinet_api import EdinetApi


class EdinetMultiDateSearchInput(BaseModel):
    """EDINET複数日付検索ツールの入力スキーマ"""
    company_name: str = Field(description="検索対象の企業名")
    document_type: Optional[str] = Field(description="書類種別", default="有価証券報告書")
    max_days_back: Optional[int] = Field(description="遡る最大日数", default=90)
    priority_days: Optional[List[int]] = Field(description="優先検索日数リスト", default=[7, 30, 90])


class EdinetMultiDateSearchTool(BaseTool):
    """EDINET複数日付遡及検索ツール"""
    
    name: str = "edinet_multi_date_search"
    description: str = """
    企業名を指定して複数の日付を遡って検索し、最新の開示書類を見つけます。
    指定された企業の最新の書類を効率的に取得できます。
    段階的に検索範囲を広げて、確実に書類を見つけます。
    """
    args_schema: type = EdinetMultiDateSearchInput
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Pydantic v2対応: model_config使用
        object.__setattr__(self, 'edinet_api', EdinetApi())
        object.__setattr__(self, '_company_name_variants', {})
    
    def _normalize_company_name(self, company_name: str) -> List[str]:
        """企業名の表記ゆれを生成"""
        variants = [company_name]
        
        # 一般的な表記ゆれパターン
        if "グループ" in company_name:
            variants.append(company_name.replace("グループ", ""))
            variants.append(company_name.replace("グループ", "ホールディングス"))
        
        if "ホールディングス" in company_name:
            variants.append(company_name.replace("ホールディングス", "グループ"))
            variants.append(company_name.replace("ホールディングス", ""))
        
        # 株式会社の有無
        if "株式会社" not in company_name:
            variants.append(f"{company_name}株式会社")
            variants.append(f"株式会社{company_name}")
        
        # カタカナ/ひらがな対応（基本的なもの）
        katakana_hiragana_map = {
            "ソフトバンク": ["ソフトバンク", "softbank"],
            "楽天": ["楽天", "rakuten"],
            "トヨタ": ["トヨタ", "toyota", "トヨタ自動車"],
            "ニトリ": ["ニトリ", "nitori"],
            "任天堂": ["任天堂", "nintendo"]
        }
        
        for key, values in katakana_hiragana_map.items():
            if key in company_name:
                for variant in values:
                    if variant != company_name:
                        variants.append(company_name.replace(key, variant))
        
        return list(set(variants))  # 重複除去
    
    def _is_weekend_or_holiday(self, date_obj: datetime) -> bool:
        """土日判定（祝日判定は簡略化）"""
        return date_obj.weekday() >= 5  # 土曜(5), 日曜(6)
    
    def _generate_search_dates(self, max_days_back: int, priority_days: List[int]) -> List[str]:
        """検索対象日付リストを生成"""
        today = datetime.now()
        search_dates = []
        
        # 優先日数での段階的検索
        for days_back in sorted(priority_days):
            if days_back > max_days_back:
                continue
                
            current_date = today
            days_searched = 0
            
            while days_searched < days_back:
                current_date -= timedelta(days=1)
                days_searched += 1
                
                # 土日をスキップ
                if self._is_weekend_or_holiday(current_date):
                    continue
                
                date_str = current_date.strftime("%Y-%m-%d")
                if date_str not in search_dates:
                    search_dates.append(date_str)
        
        return search_dates
    
    def _search_single_date(self, date_str: str, company_variants: List[str], 
                           document_type: str) -> Dict[str, Any]:
        """単一日付での検索"""
        try:
            documents_response = self.edinet_api.get_documents_list(date=date_str)
            
            if not documents_response or 'results' not in documents_response:
                return {"success": False, "date": date_str, "documents": []}
            
            # 企業名の各バリエーションで検索
            found_documents = []
            
            for doc in documents_response['results']:
                doc_description = doc.get('docDescription', '') or ''
                submitter_name = doc.get('filerName', '') or ''
                
                # 企業名のバリエーションでマッチング
                for variant in company_variants:
                    if (variant in submitter_name or variant in doc_description):
                        # 書類種別フィルタリング
                        if not document_type or document_type in doc_description:
                            found_documents.append({
                                'docID': doc.get('docID'),
                                'filerName': submitter_name,
                                'docDescription': doc_description,
                                'submitDateTime': doc.get('submitDateTime'),
                                'disclosureStatus': doc.get('disclosureStatus'),
                                'xbrlFlag': doc.get('xbrlFlag'),
                                'pdfFlag': doc.get('pdfFlag'),
                                'matched_variant': variant,
                                'search_date': date_str
                            })
                            break  # 一つのバリエーションでマッチしたら次の文書へ
            
            return {
                "success": True,
                "date": date_str,
                "documents": found_documents,
                "total_documents_checked": len(documents_response['results'])
            }
            
        except Exception as e:
            return {
                "success": False,
                "date": date_str,
                "error": str(e),
                "documents": []
            }
    
    def _run(self, company_name: str, document_type: Optional[str] = "有価証券報告書",
             max_days_back: Optional[int] = 90, 
             priority_days: Optional[List[int]] = None) -> str:
        """
        複数日付を遡って企業の書類を検索
        """
        try:
            if priority_days is None:
                priority_days = [7, 30, 90]
            
            # 企業名のバリエーションを生成
            company_variants = self._normalize_company_name(company_name)
            
            # 検索日付リストを生成
            search_dates = self._generate_search_dates(max_days_back, priority_days)
            
            all_found_documents = []
            search_log = []
            
            # 段階的検索実行
            for i, priority_range in enumerate(sorted(priority_days)):
                if priority_range > max_days_back:
                    continue
                
                stage_dates = [d for d in search_dates if d in search_dates[:priority_range]]
                stage_documents = []
                
                print(f"検索段階 {i+1}: 過去{priority_range}日間を検索中...")
                
                for date_str in stage_dates[:priority_range]:  # 段階ごとの制限
                    result = self._search_single_date(date_str, company_variants, document_type)
                    search_log.append(result)
                    
                    if result["success"] and result["documents"]:
                        stage_documents.extend(result["documents"])
                
                # この段階で見つかったら検索終了
                if stage_documents:
                    all_found_documents = stage_documents
                    print(f"段階 {i+1} で {len(stage_documents)} 件の書類を発見")
                    break
                else:
                    print(f"段階 {i+1} では書類が見つかりませんでした")
            
            # 結果の整理と返却
            if all_found_documents:
                # 最新の書類を先頭に並び替え
                all_found_documents.sort(
                    key=lambda x: x.get('submitDateTime', ''), 
                    reverse=True
                )
                
                result = {
                    "success": True,
                    "company_name": company_name,
                    "company_variants_used": company_variants,
                    "document_type": document_type,
                    "total_found": len(all_found_documents),
                    "latest_document": all_found_documents[0] if all_found_documents else None,
                    "all_documents": all_found_documents,
                    "search_summary": {
                        "dates_searched": len([log for log in search_log if log["success"]]),
                        "total_documents_checked": sum(log.get("total_documents_checked", 0) for log in search_log if log["success"]),
                        "search_ranges": priority_days
                    }
                }
            else:
                result = {
                    "success": False,
                    "company_name": company_name,
                    "company_variants_used": company_variants,
                    "document_type": document_type,
                    "message": f"指定された企業「{company_name}」の{document_type}が過去{max_days_back}日間で見つかりませんでした",
                    "total_found": 0,
                    "search_summary": {
                        "dates_searched": len([log for log in search_log if log["success"]]),
                        "total_documents_checked": sum(log.get("total_documents_checked", 0) for log in search_log if log["success"]),
                        "search_ranges": priority_days
                    }
                }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_result = {
                "success": False,
                "company_name": company_name,
                "error": str(e),
                "message": f"複数日付検索中にエラーが発生しました: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    async def _arun(self, company_name: str, document_type: Optional[str] = "有価証券報告書",
                    max_days_back: Optional[int] = 90,
                    priority_days: Optional[List[int]] = None) -> str:
        """非同期実行版"""
        return self._run(company_name, document_type, max_days_back, priority_days)