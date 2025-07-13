from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any, Optional, List
import json
import os
from ..tools.enhanced_xbrl_parser import EnhancedXbrlParser


class XbrlAnalysisInput(BaseModel):
    """XBRL解析ツールの入力スキーマ"""
    file_path: str = Field(description="解析するXBRL ZIPファイルのパス")
    analysis_type: Optional[str] = Field("financial", description="解析タイプ (financial, taxonomy, search)")
    search_terms: Optional[List[str]] = Field(None, description="検索キーワード（analysis_type='search'の場合）")


class XbrlAnalysisTool(BaseTool):
    """
    XBRLファイルを解析して財務データを抽出するLangChainツール
    """
    name: str = "xbrl_analysis"
    description: str = """XBRLファイル（ZIP形式）を解析して財務データを抽出します。企業タイプを自動判別し、適切な財務項目を抽出・整形して返します。分析結果は構造化された形式で提供され、財務分析に活用できます。"""
    args_schema: Type[BaseModel] = XbrlAnalysisInput
    
    def __init__(self):
        super().__init__()
        # Pydantic v2対応: 属性の動的設定
        object.__setattr__(self, 'parser', EnhancedXbrlParser())
    
    def _run(self, file_path: str, analysis_type: str = "financial", 
             search_terms: Optional[List[str]] = None) -> str:
        """
        XBRLファイルを解析する
        
        Args:
            file_path: XBRLファイルのパス
            analysis_type: 解析タイプ ("financial", "taxonomy", "search")
            search_terms: 検索キーワード
            
        Returns:
            str: 解析結果のJSON文字列
        """
        try:
            # ファイルの存在確認
            if not os.path.exists(file_path):
                return json.dumps({
                    "success": False,
                    "error": "FileNotFound",
                    "message": f"指定されたファイルが見つかりません: {file_path}"
                }, ensure_ascii=False, indent=2)
            
            # XBRL解析を実行
            result = self.parser.extract_xbrl_data(file_path)
            
            if not result:
                return json.dumps({
                    "success": False,
                    "error": "AnalysisError",
                    "message": "XBRLファイルの解析に失敗しました"
                }, ensure_ascii=False, indent=2)
            
            # 解析タイプに応じて結果を整形
            if analysis_type == "financial":
                return self._format_financial_analysis(result, file_path)
            elif analysis_type == "taxonomy":
                return self._format_taxonomy_analysis(result, file_path)
            elif analysis_type == "search":
                return self._format_search_analysis(result, file_path, search_terms)
            else:
                return self._format_financial_analysis(result, file_path)
                
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"XBRL解析中にエラーが発生しました: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    def _format_financial_analysis(self, result: Dict[str, Any], file_path: str) -> str:
        """財務分析結果をフォーマット"""
        financial_data = result.get('financial_data', {})
        
        # 財務データを見やすい形式に変換
        formatted_financial_data = {}
        for item_name, data in financial_data.items():
            formatted_financial_data[data['display_name']] = {
                'value': data['value'],
                'formatted_value': self._format_currency(data['value']),
                'item_code': item_name
            }
        
        analysis_result = {
            "success": True,
            "analysis_type": "financial",
            "file_path": os.path.basename(file_path),
            "company_type": result.get('company_type', 'unknown'),
            "total_elements": result.get('total_elements', 0),
            "financial_data": formatted_financial_data,
            "summary": result.get('summary_report', ''),
            "extracted_count": len(financial_data)
        }
        
        return json.dumps(analysis_result, ensure_ascii=False, indent=2)
    
    def _format_taxonomy_analysis(self, result: Dict[str, Any], file_path: str) -> str:
        """タクソノミ分析結果をフォーマット"""
        analysis_result = {
            "success": True,
            "analysis_type": "taxonomy",
            "file_path": os.path.basename(file_path),
            "company_type": result.get('company_type', 'unknown'),
            "total_elements": result.get('total_elements', 0),
            "available_columns": result.get('available_columns', []),
            "summary": f"企業タイプ: {result.get('company_type', 'unknown')}, 総要素数: {result.get('total_elements', 0)}"
        }
        
        return json.dumps(analysis_result, ensure_ascii=False, indent=2)
    
    def _format_search_analysis(self, result: Dict[str, Any], file_path: str, 
                               search_terms: Optional[List[str]]) -> str:
        """検索分析結果をフォーマット"""
        if not search_terms:
            search_terms = ["資産", "利益", "売上"]
        
        # 検索機能を実行
        search_results = []
        for term in search_terms:
            search_result = self.parser.search_financial_items([term])
            if not search_result.empty:
                search_results.append({
                    "search_term": term,
                    "matches": search_result.to_dict('records')[:5]  # 上位5件
                })
        
        analysis_result = {
            "success": True,
            "analysis_type": "search",
            "file_path": os.path.basename(file_path),
            "company_type": result.get('company_type', 'unknown'),
            "search_terms": search_terms,
            "search_results": search_results,
            "total_matches": sum(len(sr['matches']) for sr in search_results)
        }
        
        return json.dumps(analysis_result, ensure_ascii=False, indent=2)
    
    def _format_currency(self, value: float) -> str:
        """金額を見やすい形式にフォーマット"""
        if value is None:
            return "N/A"
        
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}億円"
        elif abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.2f}百万円"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.2f}千円"
        else:
            return f"{value:.0f}円"
    
    async def _arun(self, file_path: str, analysis_type: str = "financial",
                    search_terms: Optional[List[str]] = None) -> str:
        """非同期実行版"""
        return self._run(file_path, analysis_type, search_terms)


class XbrlComparisonInput(BaseModel):
    """XBRL比較ツールの入力スキーマ"""
    file_paths: List[str] = Field(description="比較するXBRL ZIPファイルのパスリスト")
    comparison_items: Optional[List[str]] = Field(None, description="比較する財務項目のリスト")


class XbrlComparisonTool(BaseTool):
    """
    複数のXBRLファイルの財務データを比較するLangChainツール
    """
    name: str = "xbrl_comparison"
    description: str = """複数のXBRLファイルを解析して財務データを比較します。企業の期間比較や複数企業の比較分析に使用できます。比較結果は構造化されたデータとして提供されます。"""
    args_schema: Type[BaseModel] = XbrlComparisonInput
    
    def __init__(self):
        super().__init__()
        # Pydantic v2対応: 属性の動的設定
        object.__setattr__(self, 'parser', EnhancedXbrlParser())
    
    def _run(self, file_paths: List[str], 
             comparison_items: Optional[List[str]] = None) -> str:
        """
        複数のXBRLファイルを比較する
        
        Args:
            file_paths: XBRLファイルのパスリスト
            comparison_items: 比較する財務項目
            
        Returns:
            str: 比較結果のJSON文字列
        """
        try:
            comparison_results = []
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    comparison_results.append({
                        "file_path": os.path.basename(file_path),
                        "success": False,
                        "error": "FileNotFound"
                    })
                    continue
                
                result = self.parser.extract_xbrl_data(file_path)
                if result:
                    financial_data = result.get('financial_data', {})
                    formatted_data = {}
                    
                    for item_name, data in financial_data.items():
                        formatted_data[data['display_name']] = data['value']
                    
                    comparison_results.append({
                        "file_path": os.path.basename(file_path),
                        "success": True,
                        "company_type": result.get('company_type', 'unknown'),
                        "financial_data": formatted_data
                    })
                else:
                    comparison_results.append({
                        "file_path": os.path.basename(file_path),
                        "success": False,
                        "error": "AnalysisError"
                    })
            
            # 比較分析を実行
            comparison_analysis = self._perform_comparison_analysis(
                comparison_results, comparison_items
            )
            
            final_result = {
                "success": True,
                "comparison_type": "multi_file",
                "total_files": len(file_paths),
                "successful_analyses": len([r for r in comparison_results if r.get('success')]),
                "individual_results": comparison_results,
                "comparison_analysis": comparison_analysis
            }
            
            return json.dumps(final_result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": f"XBRL比較中にエラーが発生しました: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
    
    def _perform_comparison_analysis(self, results: List[Dict], 
                                   comparison_items: Optional[List[str]]) -> Dict:
        """比較分析を実行"""
        successful_results = [r for r in results if r.get('success')]
        
        if len(successful_results) < 2:
            return {"error": "比較には少なくとも2つの有効なファイルが必要です"}
        
        # 共通の財務項目を特定
        all_items = set()
        for result in successful_results:
            financial_data = result.get('financial_data', {})
            all_items.update(financial_data.keys())
        
        if comparison_items:
            # 指定された項目のみを比較
            comparison_keys = [item for item in comparison_items if item in all_items]
        else:
            # 全ての共通項目を比較
            comparison_keys = list(all_items)
        
        comparison_data = {}
        for item in comparison_keys:
            item_values = []
            for result in successful_results:
                financial_data = result.get('financial_data', {})
                value = financial_data.get(item)
                item_values.append({
                    "file": result['file_path'],
                    "value": value
                })
            
            comparison_data[item] = {
                "values": item_values,
                "min_value": min([v['value'] for v in item_values if v['value'] is not None], default=None),
                "max_value": max([v['value'] for v in item_values if v['value'] is not None], default=None)
            }
        
        return {
            "compared_items": comparison_keys,
            "comparison_data": comparison_data,
            "summary": f"{len(comparison_keys)}項目を{len(successful_results)}ファイル間で比較"
        }
    
    async def _arun(self, file_paths: List[str],
                    comparison_items: Optional[List[str]] = None) -> str:
        """非同期実行版"""
        return self._run(file_paths, comparison_items)


if __name__ == "__main__":
    # テスト実行用のコード
    analysis_tool = XbrlAnalysisTool()
    
    # 財務分析テスト
    print("=== XBRL財務分析テスト ===")
    test_file = "temp_downloads/S100VVBR_xbrl.zip"
    if os.path.exists(test_file):
        result = analysis_tool._run(test_file, "financial")
        print(result)
    else:
        print(f"テストファイルが見つかりません: {test_file}")
    
    # 検索分析テスト
    print("\n=== XBRL検索分析テスト ===")
    if os.path.exists(test_file):
        result = analysis_tool._run(test_file, "search", ["資産", "利益"])
        print(result)