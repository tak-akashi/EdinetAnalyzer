import pandas as pd
import re
from typing import Dict, List, Optional, Any

class FinancialExtractor:
    """
    XBRLデータから動的に財務データを抽出するクラス
    """
    
    def __init__(self, mapping_config):
        self.mapping_config = mapping_config
    
    def extract_financial_data(self, df: pd.DataFrame, company_type: str) -> Dict[str, Any]:
        """
        DataFrameから財務データを抽出する
        
        Args:
            df (pd.DataFrame): XBRLデータのDataFrame
            company_type (str): 企業タイプ
            
        Returns:
            Dict[str, Any]: 抽出された財務データ
        """
        if df.empty or '要素ID' not in df.columns:
            return {}
        
        mapping = self.mapping_config.get_mapping_for_company_type(company_type)
        if not mapping:
            return {}
        
        extracted_data = {}
        
        for item_name, config in mapping.items():
            value = self._extract_single_item(df, item_name, config, company_type)
            if value is not None:
                extracted_data[item_name] = {
                    'value': value,
                    'display_name': config['display_name'],
                    'item_name': item_name
                }
        
        return extracted_data
    
    def _extract_single_item(self, df: pd.DataFrame, item_name: str, 
                           config: Dict, company_type: str) -> Optional[float]:
        """
        単一の財務項目を抽出する
        """
        element_ids = config['element_ids']
        context_priority = config.get('context_priority', [])
        member_priority = config.get('member_priority', [])
        
        # 要素IDでフィルタリング
        filtered_df = df[df['要素ID'].isin(element_ids)]
        
        if filtered_df.empty:
            # 部分一致による検索
            filtered_df = self._fuzzy_search_elements(df, element_ids)
        
        if filtered_df.empty:
            return None
        
        # 優先順位に基づいて最適な値を選択
        best_value = self._select_best_value(filtered_df, context_priority, member_priority)
        
        return best_value
    
    def _fuzzy_search_elements(self, df: pd.DataFrame, target_element_ids: List[str]) -> pd.DataFrame:
        """
        要素IDの部分一致検索
        """
        patterns = []
        
        for element_id in target_element_ids:
            # プレフィックスを除いた部分でも検索
            if ':' in element_id:
                suffix = element_id.split(':')[1]
                patterns.append(suffix)
            patterns.append(element_id)
        
        matched_rows = []
        for pattern in patterns:
            # 正規表現による柔軟な検索
            pattern_regex = re.compile(re.escape(pattern), re.IGNORECASE)
            matches = df[df['要素ID'].str.contains(pattern_regex, na=False)]
            if not matches.empty:
                matched_rows.append(matches)
        
        if matched_rows:
            return pd.concat(matched_rows).drop_duplicates()
        
        return pd.DataFrame()
    
    def _select_best_value(self, df: pd.DataFrame, context_priority: List[str], 
                          member_priority: List[str]) -> Optional[float]:
        """
        優先順位に基づいて最適な値を選択
        """
        if df.empty:
            return None
        
        # 数値として解釈可能な値のみを対象とする
        df = df.copy()
        df['値_numeric'] = pd.to_numeric(df['値'], errors='coerce')
        df = df.dropna(subset=['値_numeric'])
        
        if df.empty:
            return None
        
        # コンテキスト優先順位で絞り込み
        best_df = self._filter_by_priority(df, 'コンテキストID', context_priority)
        
        # 連結・個別優先順位で絞り込み
        if '連結・個別' in best_df.columns and member_priority:
            member_filtered = self._filter_by_priority(best_df, '連結・個別', member_priority)
            if not member_filtered.empty:
                best_df = member_filtered
        
        # 相対年度で「当期」を優先
        if '相対年度' in best_df.columns:
            current_year = best_df[best_df['相対年度'].str.contains('当期', na=False)]
            if not current_year.empty:
                best_df = current_year
        
        # 最初の値を返す
        if not best_df.empty:
            return float(best_df['値_numeric'].iloc[0])
        
        return None
    
    def _filter_by_priority(self, df: pd.DataFrame, column: str, 
                           priorities: List[str]) -> pd.DataFrame:
        """
        優先順位リストに基づいてDataFrameをフィルタリング
        """
        for priority in priorities:
            filtered = df[df[column].str.contains(priority, na=False)]
            if not filtered.empty:
                return filtered
        
        return df
    
    def search_available_elements(self, df: pd.DataFrame, search_terms: List[str]) -> pd.DataFrame:
        """
        指定されたキーワードで利用可能な要素IDを検索
        """
        if df.empty or '要素ID' not in df.columns:
            return pd.DataFrame()
        
        search_results = []
        
        for term in search_terms:
            # 要素IDでの検索
            element_matches = df[df['要素ID'].str.contains(term, case=False, na=False)]
            
            # 項目名での検索
            if '項目名' in df.columns:
                name_matches = df[df['項目名'].str.contains(term, case=False, na=False)]
                element_matches = pd.concat([element_matches, name_matches]).drop_duplicates()
            
            if not element_matches.empty:
                search_results.append(element_matches)
        
        if search_results:
            combined_results = pd.concat(search_results).drop_duplicates()
            return combined_results[['要素ID', '項目名', '値']].head(20)  # 上位20件
        
        return pd.DataFrame()
    
    def generate_summary_report(self, extracted_data: Dict[str, Any], 
                               company_type: str) -> str:
        """
        抽出されたデータのサマリーレポートを生成
        """
        if not extracted_data:
            return "財務データの抽出に失敗しました。"
        
        report = f"\n=== 財務データ抽出結果 ({company_type}) ===\n"
        
        for item_name, data in extracted_data.items():
            display_name = data['display_name']
            value = data['value']
            
            if isinstance(value, (int, float)):
                if abs(value) >= 1_000_000_000:
                    formatted_value = f"{value / 1_000_000_000:.2f}億円"
                elif abs(value) >= 1_000_000:
                    formatted_value = f"{value / 1_000_000:.2f}百万円"
                elif abs(value) >= 1_000:
                    formatted_value = f"{value / 1_000:.2f}千円"
                else:
                    formatted_value = f"{value:.0f}円"
            else:
                formatted_value = str(value)
            
            report += f"{display_name}: {formatted_value}\n"
        
        return report
    
    def export_to_dataframe(self, extracted_data: Dict[str, Any]) -> pd.DataFrame:
        """
        抽出されたデータをDataFrameとして出力
        """
        if not extracted_data:
            return pd.DataFrame()
        
        rows = []
        for item_name, data in extracted_data.items():
            rows.append({
                'item_name': item_name,
                'display_name': data['display_name'],
                'value': data['value']
            })
        
        return pd.DataFrame(rows)

if __name__ == '__main__':
    # テスト用のサンプルコード
    from .financial_mapping import FinancialMapping
    import os
    import zipfile
    import glob
    import chardet
    
    # マッピング設定を読み込み
    mapping = FinancialMapping()
    extractor = FinancialExtractor(mapping)
    
    # 既存のXBRLファイルでテスト
    xbrl_files = glob.glob("temp_downloads/*_xbrl.zip")
    
    if xbrl_files:
        test_file = xbrl_files[0]
        print(f"テストファイル: {test_file}")
        
        # ZIPファイルを展開してCSVを読み込み
        extract_dir = "temp_test_extract"
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(test_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            csv_files = glob.glob(os.path.join(extract_dir, '**', '*.csv'), recursive=True)
            
            if csv_files:
                all_data = []
                for csv_file in csv_files:
                    try:
                        with open(csv_file, 'rb') as f:
                            raw_data = f.read(10000)
                            detection = chardet.detect(raw_data)
                            encoding = detection['encoding']
                        
                        if encoding:
                            df_csv = pd.read_csv(csv_file, encoding=encoding, sep='\t', encoding_errors='ignore')
                            all_data.append(df_csv)
                    except Exception as e:
                        print(f"CSVファイル読み込みエラー: {e}")
                        continue
                
                if all_data:
                    combined_df = pd.concat(all_data, ignore_index=True)
                    
                    # 投資信託として財務データを抽出
                    extracted = extractor.extract_financial_data(combined_df, "investment_trust")
                    
                    # 結果を表示
                    print(extractor.generate_summary_report(extracted, "investment_trust"))
                    
                    # DataFrame出力
                    result_df = extractor.export_to_dataframe(extracted)
                    if not result_df.empty:
                        print("\n=== DataFrame形式 ===")
                        print(result_df.to_string())
        
        except Exception as e:
            print(f"テスト実行エラー: {e}")
    else:
        print("テスト用のXBRLファイルが見つかりません")