import os
import zipfile
import pandas as pd
import glob
import chardet
from .taxonomy_analyzer import TaxonomyAnalyzer
from .financial_mapping import FinancialMapping
from .financial_extractor import FinancialExtractor

class EnhancedXbrlParser:
    """
    拡張されたXBRLデータ解析クラス（新機能統合版）
    """
    def __init__(self):
        self.taxonomy_analyzer = TaxonomyAnalyzer()
        self.financial_mapping = FinancialMapping()
        self.financial_extractor = FinancialExtractor(self.financial_mapping)
        self.company_type = None
        self.combined_df = None
        self._last_result = None
    
    def extract_xbrl_data(self, zip_file_path: str, extract_dir: str = "temp_xbrl_extracted"):
        """
        XBRLのZIPファイル（CSV形式）を展開し、財務データを抽出する（新機能統合版）

        Args:
            zip_file_path (str): ダウンロードしたXBRLのZIPファイルのパス
            extract_dir (str): 展開するディレクトリ

        Returns:
            dict: 抽出された財務データと分析情報
        """
        if not os.path.exists(zip_file_path):
            print(f"エラー: 指定されたZIPファイルが見つかりません: {zip_file_path}")
            return None

        os.makedirs(extract_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"ZIPファイルを {extract_dir} に展開しました。")
        except zipfile.BadZipFile:
            print(f"エラー: 不正なZIPファイルです: {zip_file_path}")
            return None
        except Exception as e:
            print(f"ZIPファイルの展開中にエラーが発生しました: {e}")
            return None

        # CSVファイルを読み込み
        csv_files = glob.glob(os.path.join(extract_dir, '**', '*.csv'), recursive=True)
        
        if not csv_files:
            print(f"エラー: 展開されたファイルからCSVファイルが見つかりませんでした。")
            return None

        all_data = []
        for csv_file in csv_files:
            try:
                with open(csv_file, 'rb') as f:
                    raw_data = f.read(10000)
                    detection = chardet.detect(raw_data)
                    encoding = detection['encoding']
                    print(f"検出されたエンコーディング: {encoding} for {csv_file}")

                if encoding:
                    df_csv = pd.read_csv(csv_file, encoding=encoding, sep='\t', encoding_errors='ignore')
                    all_data.append(df_csv)
                    print(f"CSVファイルを読み込みました: {csv_file}")

            except Exception as e:
                print(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
                continue
        
        if not all_data:
            print("エラー: 読み込めるCSVファイルがありませんでした。")
            return None

        # 全てのCSVデータを連結
        self.combined_df = pd.concat(all_data, ignore_index=True)
        print(f"Combined DataFrame Columns: {self.combined_df.columns.tolist()}")

        # 企業タイプを自動判別
        self.company_type = self._detect_company_type()
        print(f"検出された企業タイプ: {self.company_type}")

        # 新しい抽出機能を使用
        extracted_data = self.financial_extractor.extract_financial_data(
            self.combined_df, self.company_type
        )

        # 結果をまとめて返す
        result = {
            'financial_data': extracted_data,
            'company_type': self.company_type,
            'total_elements': len(self.combined_df) if not self.combined_df.empty else 0,
            'available_columns': self.combined_df.columns.tolist() if not self.combined_df.empty else [],
            'summary_report': self.financial_extractor.generate_summary_report(
                extracted_data, self.company_type
            )
        }

        self._last_result = result
        return result
    
    def _detect_company_type(self):
        """
        CSVデータから企業タイプを判別
        """
        if self.combined_df is None or self.combined_df.empty:
            return "unknown"
        
        if '要素ID' not in self.combined_df.columns:
            return "unknown"
        
        elements = self.combined_df['要素ID'].dropna().unique()
        return self.taxonomy_analyzer._detect_company_type(elements)
    
    def get_financial_summary(self):
        """
        財務データのサマリーをDataFrame形式で取得
        """
        if not hasattr(self, '_last_result') or self._last_result is None:
            return pd.DataFrame()
        
        financial_data = self._last_result.get('financial_data', {})
        return self.financial_extractor.export_to_dataframe(financial_data)
    
    def search_financial_items(self, search_terms: list):
        """
        指定されたキーワードで財務項目を検索
        """
        if self.combined_df is None or self.combined_df.empty:
            print("データが読み込まれていません。まずextract_xbrl_dataを実行してください。")
            return pd.DataFrame()
        
        return self.financial_extractor.search_available_elements(
            self.combined_df, search_terms
        )
    
    def get_detailed_analysis(self):
        """
        詳細分析結果を取得
        """
        if self._last_result is None:
            return "データが読み込まれていません。"
        
        analysis = f"""
=== 詳細分析結果 ===
企業タイプ: {self._last_result['company_type']}
総要素数: {self._last_result['total_elements']}
利用可能カラム: {', '.join(self._last_result['available_columns'])}

{self._last_result['summary_report']}

=== 抽出された財務データ ===
"""
        
        financial_data = self._last_result.get('financial_data', {})
        for item_name, data in financial_data.items():
            analysis += f"- {data['display_name']}: {data['value']}\n"
        
        return analysis
    
    def export_to_csv(self, output_file: str = "extracted_financial_data.csv"):
        """
        抽出された財務データをCSVファイルに出力
        """
        df = self.get_financial_summary()
        if not df.empty:
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"財務データを {output_file} に出力しました。")
        else:
            print("出力する財務データがありません。")

if __name__ == '__main__':
    # テスト実行
    parser = EnhancedXbrlParser()
    
    # 既存のXBRLファイルでテスト
    xbrl_files = glob.glob("temp_downloads/*_xbrl.zip")
    
    if xbrl_files:
        test_file = xbrl_files[0]
        print(f"=== {test_file} を解析中 ===")
        
        # データ抽出
        result = parser.extract_xbrl_data(test_file)
        
        if result:
            # 詳細分析結果を表示
            print(parser.get_detailed_analysis())
            
            # DataFrameとして表示
            df_summary = parser.get_financial_summary()
            if not df_summary.empty:
                print("\n=== DataFrame形式 ===")
                print(df_summary.to_string())
            
            # CSVに出力
            parser.export_to_csv("test_financial_data.csv")
            
            # 検索機能のテスト
            print("\n=== 検索機能テスト（'資産'で検索）===")
            search_result = parser.search_financial_items(['資産'])
            if not search_result.empty:
                print(search_result.to_string())
        else:
            print("データの抽出に失敗しました。")
    else:
        print("テスト用のXBRLファイルが見つかりません。")