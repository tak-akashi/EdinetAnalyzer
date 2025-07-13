import os
import zipfile
import pandas as pd
import glob
import chardet # chardetモジュールを追加
from .taxonomy_analyzer import TaxonomyAnalyzer
from .financial_mapping import FinancialMapping
from .financial_extractor import FinancialExtractor

class XbrlParser:
    """
    XBRLデータをCSVファイルから解析し、財務データを抽出するクラス
    """
    def __init__(self):
        self.taxonomy_analyzer = TaxonomyAnalyzer()
        self.financial_mapping = FinancialMapping()
        self.financial_extractor = FinancialExtractor(self.financial_mapping)
        self.company_type = None
        self.combined_df = None 

    def extract_xbrl_data(self, zip_file_path: str, extract_dir: str = "temp_xbrl_extracted"):
        """
        XBRLのZIPファイル（CSV形式）を展開し、主要な財務データを抽出する

        Args:
            zip_file_path (str): ダウンロードしたXBRLのZIPファイルのパス
            extract_dir (str): 展開するディレクトリ

        Returns:
            pd.DataFrame: 抽出された財務データ
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

        # 展開されたディレクトリ内のCSVファイルを探す
        csv_files = glob.glob(os.path.join(extract_dir, '**', '*.csv'), recursive=True)
        
        if not csv_files:
            print(f"エラー: 展開されたファイルからCSVファイルが見つかりませんでした。")
            return None

        # 複数のCSVファイルがある場合、どのCSVを読み込むか判断する必要がある
        # ここでは、一旦全てのCSVファイルを読み込み、連結する
        all_data = []
        for csv_file in csv_files:
            try:
                # ファイルのエンコーディングを自動判別
                with open(csv_file, 'rb') as f:
                    raw_data = f.read(10000) # 最初の10000バイトで判別
                    detection = chardet.detect(raw_data)
                    encoding = detection['encoding']
                    confidence = detection['confidence']
                    print(f"検出されたエンコーディング: {encoding} (信頼度: {confidence}) for {csv_file}")

                if encoding:
                    df_csv = pd.read_csv(csv_file, encoding=encoding, sep='\t', encoding_errors='ignore')
                    all_data.append(df_csv)
                    print(f"CSVファイルを読み込みました: {csv_file}")
                else:
                    print(f"エラー: エンコーディングを判別できませんでした: {csv_file}")

            except Exception as e:
                print(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
                continue
        
        if not all_data:
            print("エラー: 読み込めるCSVファイルがありませんでした。")
            return None

        # 全てのCSVデータを連結
        combined_df = pd.concat(all_data, ignore_index=True)

        # ここから、combined_dfから必要な財務データを抽出するロジックを記述
        # EDINETのCSVフォーマットに依存するため、具体的な項目名を指定する必要がある
        # EDINETのXBRL-CSVは、通常、以下のようなカラムを持つ
        # '項目ID', '項目名', '値', '単位', '期間', ...
        # ただし、XBRLタクソノミIDが直接カラム名になっている場合もある

        # 実際のCSVのカラム名を確認するために、combined_df.columns を出力してみる
        print(f"Combined DataFrame Columns: {combined_df.columns.tolist()}")

        # XBRLタクソノミIDと、抽出したい財務データの項目名をマッピングする
        # 実際のCSVのカラム名や、XBRLタクソノミIDに合わせて調整が必要です。
        financial_items_mapping = {
            "NetSales": "NetSales", # 売上高 (要素IDがそのまま英語名の場合)
            "OperatingIncome": "OperatingIncome", # 営業利益
            "OrdinaryIncome": "OrdinaryIncome", # 経常利益
            "ProfitLoss": "ProfitLoss", # 当期純利益
            "Assets": "Assets", # 資産合計
            "Liabilities": "Liabilities", # 負債合計
            "Equity": "Equity", # 純資産合計
            # 必要に応じて項目を追加
            # EDINETのXBRL-CSVの要素IDは、タクソノミによって異なるため、
            # 実際のCSVファイルの内容を確認して正確な要素IDを設定する必要があります。
            # 例: 'jpfr-t-qci:NetSales' のようなプレフィックスが付く場合もあります。
            # 今回のテストファイルでは、プレフィックスなしの英語名が要素IDになっていると仮定します。
        }

        extracted_data = {}
        # CSVに'要素ID'と'値'のカラムが存在すると仮定
        if '要素ID' in combined_df.columns and '値' in combined_df.columns:
            for xbrl_id_key, en_name in financial_items_mapping.items():
                # 要素IDが一致する行をフィルタリング
                filtered_rows = combined_df[combined_df['要素ID'] == xbrl_id_key]
                if not filtered_rows.empty:
                    # 最新の期間や特定の条件で値を選択する必要があるが、ここでは単純に最初の値を取得
                    extracted_data[en_name] = filtered_rows['値'].iloc[0]
        else:
            print("エラー: CSVファイルに'要素ID'または'値'カラムが見つかりませんでした。")
        
        df_result = pd.DataFrame([extracted_data])
        return df_result

if __name__ == '__main__':
    # テスト実行用のコード
    # edinet_api.pyで生成されるファイル名パターンに合わせる
    import glob as glob_module
    xbrl_files = glob_module.glob("temp_downloads/*_xbrl.zip")
    if xbrl_files:
        test_zip_file = xbrl_files[0]  # 最初に見つかったXBRLファイルを使用
    else:
        test_zip_file = "temp_downloads/example_xbrl.zip"  # フォールバック 
    extract_dir = "temp_xbrl_extracted"

    # デバッグ用: CSVファイルの内容を直接表示
    if os.path.exists(test_zip_file):
        with zipfile.ZipFile(test_zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        csv_files = glob.glob(os.path.join(extract_dir, '**', '*.csv'), recursive=True)
        if csv_files:
            print("\n--- CSVファイル内容の確認 ---")
            for csv_file in csv_files:
                try:
                    with open(csv_file, 'rb') as f:
                        raw_data = f.read()
                        detection = chardet.detect(raw_data)
                        encoding = detection['encoding']
                        print(f"ファイル: {csv_file}, エンコーディング: {encoding}")
                        if encoding:
                            with open(csv_file, 'r', encoding=encoding, errors='ignore') as f_decoded:
                                print(f_decoded.read(500)) # 先頭500文字を表示
                        else:
                            print(f"エラー: エンコーディングを判別できませんでした: {csv_file}")
                except Exception as e:
                    print(f"ファイル読み込みエラー: {csv_file}, {e}")
            print("--- CSVファイル内容の確認 終了 ---\n")

    if os.path.exists(test_zip_file):
        print("--- XBRL解析テスト ---")
        parser = XbrlParser()
        df_xbrl = parser.extract_xbrl_data(test_zip_file, extract_dir)

        if df_xbrl is not None and not df_xbrl.empty:
            print("\nXBRLデータ抽出成功:")
            print(df_xbrl.to_string())
        else:
            print("\nXBRLデータ抽出失敗またはデータがありません。")
    else:
        print(f"テスト用のXBRL ZIPファイルが見つかりません: {test_zip_file}")
        print("edinet_api.py を実行して、先にファイルをダウンロードしてください。")