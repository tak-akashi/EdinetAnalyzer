import os
import zipfile
import pandas as pd
import glob
import chardet
from collections import Counter
import json

class TaxonomyAnalyzer:
    """
    XBRLデータのタクソノミIDを分析し、企業タイプや利用可能な項目を特定するクラス
    """
    
    def __init__(self):
        self.element_stats = {}
        self.company_types = {
            'investment_trust': ['jppfs_cor:', 'jpfund_'],
            'general_company': ['jpfr-', 'jpcrp_', 'jpdei_cor:'],
            'bank': ['jpbank_'],
            'insurance': ['jpins_']
        }
    
    def analyze_xbrl_zip(self, zip_file_path: str, extract_dir: str = "temp_taxonomy_analysis"):
        """
        XBRLのZIPファイルからタクソノミIDを分析する
        
        Args:
            zip_file_path (str): XBRLのZIPファイルパス
            extract_dir (str): 一時展開ディレクトリ
            
        Returns:
            dict: 分析結果
        """
        if not os.path.exists(zip_file_path):
            print(f"エラー: 指定されたZIPファイルが見つかりません: {zip_file_path}")
            return None
        
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except zipfile.BadZipFile:
            print(f"エラー: 不正なZIPファイル: {zip_file_path}")
            return None
        
        # CSVファイルを探して読み込み
        csv_files = glob.glob(os.path.join(extract_dir, '**', '*.csv'), recursive=True)
        
        if not csv_files:
            print("CSVファイルが見つかりませんでした")
            return None
        
        all_elements = []
        company_type = "unknown"
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'rb') as f:
                    raw_data = f.read(10000)
                    detection = chardet.detect(raw_data)
                    encoding = detection['encoding']
                
                if encoding:
                    df = pd.read_csv(csv_file, encoding=encoding, sep='\t', encoding_errors='ignore')
                    
                    if '要素ID' in df.columns:
                        elements = df['要素ID'].dropna().unique()
                        all_elements.extend(elements)
                        
            except Exception as e:
                print(f"CSVファイル読み込みエラー: {csv_file}, {e}")
                continue
        
        # 企業タイプを判別
        company_type = self._detect_company_type(all_elements)
        
        # 要素IDの統計情報を作成
        element_counter = Counter(all_elements)
        
        # 財務項目の候補を抽出
        financial_candidates = self._extract_financial_candidates(all_elements, company_type)
        
        analysis_result = {
            'company_type': company_type,
            'total_elements': len(all_elements),
            'unique_elements': len(element_counter),
            'element_frequency': dict(element_counter.most_common(50)),
            'financial_candidates': financial_candidates,
            'prefixes': self._analyze_prefixes(all_elements)
        }
        
        return analysis_result
    
    def _detect_company_type(self, elements):
        """要素IDから企業タイプを判別"""
        type_scores = {}
        
        for company_type, prefixes in self.company_types.items():
            score = 0
            for element in elements:
                for prefix in prefixes:
                    if element.startswith(prefix):
                        score += 1
            type_scores[company_type] = score
        
        if not type_scores or max(type_scores.values()) == 0:
            return "unknown"
        
        return max(type_scores, key=type_scores.get)
    
    def _analyze_prefixes(self, elements):
        """要素IDのプレフィックスを分析"""
        prefixes = []
        for element in elements:
            if ':' in element:
                prefix = element.split(':')[0] + ':'
                prefixes.append(prefix)
        
        return dict(Counter(prefixes).most_common(20))
    
    def _extract_financial_candidates(self, elements, company_type):
        """財務項目の候補を抽出"""
        candidates = {}
        
        if company_type == "investment_trust":
            keywords = {
                'assets': ['資産', 'Assets', 'Asset'],
                'net_assets': ['純資産', 'NetAssets', 'Equity'],
                'investment_securities': ['投資', 'Investment', 'Securities'],
                'call_loans': ['コール', 'Call', 'Loans']
            }
        else:
            keywords = {
                'sales': ['売上', 'Sales', 'Revenue', 'NetSales'],
                'operating_income': ['営業利益', 'OperatingIncome', 'Operating'],
                'ordinary_income': ['経常利益', 'OrdinaryIncome', 'Ordinary'],
                'net_income': ['当期純利益', 'NetIncome', 'ProfitLoss'],
                'total_assets': ['資産合計', 'TotalAssets', 'Assets'],
                'total_liabilities': ['負債合計', 'TotalLiabilities', 'Liabilities'],
                'net_assets': ['純資産', 'NetAssets', 'Equity']
            }
        
        for category, search_terms in keywords.items():
            matched_elements = []
            for element in elements:
                for term in search_terms:
                    if term.lower() in element.lower():
                        matched_elements.append(element)
            candidates[category] = list(set(matched_elements))
        
        return candidates
    
    def save_analysis_result(self, result, output_file="taxonomy_analysis.json"):
        """分析結果をJSONファイルに保存"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"分析結果を {output_file} に保存しました")
    
    def print_analysis_summary(self, result):
        """分析結果のサマリーを表示"""
        print("\n=== タクソノミ分析結果 ===")
        print(f"企業タイプ: {result['company_type']}")
        print(f"総要素数: {result['total_elements']}")
        print(f"ユニーク要素数: {result['unique_elements']}")
        
        print("\n--- 主要プレフィックス ---")
        for prefix, count in list(result['prefixes'].items())[:10]:
            print(f"{prefix}: {count}")
        
        print("\n--- 財務項目候補 ---")
        for category, candidates in result['financial_candidates'].items():
            print(f"{category}:")
            for candidate in candidates[:3]:  # 上位3つまで表示
                print(f"  - {candidate}")
            if len(candidates) > 3:
                print(f"  ... 他{len(candidates)-3}件")
            print()

if __name__ == '__main__':
    analyzer = TaxonomyAnalyzer()
    
    # 既存のXBRLファイルを分析
    xbrl_files = glob.glob("temp_downloads/*_xbrl.zip")
    
    if not xbrl_files:
        print("分析対象のXBRLファイルが見つかりません")
        print("edinet_api.py を実行してファイルをダウンロードしてください")
    else:
        for xbrl_file in xbrl_files:
            print(f"\n=== {xbrl_file} を分析中 ===")
            result = analyzer.analyze_xbrl_zip(xbrl_file)
            
            if result:
                analyzer.print_analysis_summary(result)
                
                # 結果をファイルに保存
                output_file = f"taxonomy_analysis_{os.path.basename(xbrl_file).replace('.zip', '.json')}"
                analyzer.save_analysis_result(result, output_file)