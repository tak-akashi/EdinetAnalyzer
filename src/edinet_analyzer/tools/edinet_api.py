import os
import requests
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class EdinetApi:
    """
    EDINET APIと通信するためのクライアントクラス
    """
    BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"

    def __init__(self):
        self.api_key = os.getenv("EDINET_API_KEY")
        if not self.api_key:
            raise ValueError("EDINET_API_KEYが設定されていません。")

    def get_documents_list(self, date: str = None, type: int = 2):
        """
        指定された日付の書類一覧を取得する

        Args:
            date (str, optional): 取得対象の日付 (YYYY-MM-DD)。デフォルトは前日。
            type (int, optional): 書類種別 (1:提出本文書及び監査報告書、2:PDF)。デフォルトは2。

        Returns:
            dict: APIからのレスポンス(JSON)
        """
        if date is None:
            # デフォルトは前日の日付
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/documents.json"
        params = {
            "date": date,
            "type": type,
            "Subscription-Key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"APIリクエスト中にエラーが発生しました: {e}")
            return None

    def download_xbrl_document(self, doc_id: str):
        """
        指定されたdocIDのXBRL書類をダウンロードして保存する

        Args:
            doc_id (str): 書類管理番号

        Returns:
            str: 保存したファイルパス、失敗した場合はNone
        """
        save_dir = "temp_downloads"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{doc_id}_xbrl.zip")
        
        # type=5 for XBRL
        success = self.download_document(doc_id, save_path, type=5)
        return save_path if success else None
    
    def download_main_document(self, doc_id: str):
        """
        指定されたdocIDのメイン書類をダウンロードして保存する

        Args:
            doc_id (str): 書類管理番号

        Returns:
            str: 保存したファイルパス、失敗した場合はNone
        """
        save_dir = "temp_downloads"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{doc_id}_main.zip")
        
        # type=1 for main document
        success = self.download_document(doc_id, save_path, type=1)
        return save_path if success else None
    
    def download_document(self, doc_id: str, save_path: str, type: int = 1):
        """
        指定されたdocIDの書類をダウンロードして保存する

        Args:
            doc_id (str): 書類管理番号
            save_path (str): 保存先のファイルパス (例: "./S100ABC.zip")
            type (int, optional): 書類種別 (1:提出本文書及び監査報告書, 5:XBRL形式). デフォルトは1。

        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        # 書類ダウンロードは別のエンドポイントを利用する
        download_base_url = "https://api.edinet-fsa.go.jp/api/v2"
        url = f"{download_base_url}/documents/{doc_id}"
        
        params = {
            "type": type,
            "Subscription-Key": self.api_key
        }

        try:
            with requests.get(url, params=params, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            print(f"書類を {save_path} に保存しました。")
            return True
        except requests.exceptions.RequestException as e:
            print(f"書類のダウンロード中にエラーが発生しました: {e}")
            return False
        except IOError as e:
            print(f"ファイル保存中にエラーが発生しました: {e}")
            return False

if __name__ == '__main__':
    import argparse
    
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='EDINET APIから書類を取得・ダウンロード')
    parser.add_argument('--date', '-d', type=str, help='取得対象の日付 (YYYY-MM-DD形式)', default=None)
    parser.add_argument('--type', '-t', type=int, choices=[1, 2], help='書類種別 (1:提出本文書及び監査報告書、2:PDF)', default=2)
    
    args = parser.parse_args()
    
    if args.date:
        print(f"指定された日付: {args.date}")
    else:
        print("日付が指定されていません。前日の日付を使用します。")
    
    try:
        api = EdinetApi()
        # 指定された引数でリストを取得
        documents_res = api.get_documents_list(date=args.date, type=args.type) 
        
        if not (documents_res and documents_res.get("results")):
            print("書類リストの取得に失敗したか、対象の書類がありません。")
            if documents_res:
                print(f"メタデータ: {documents_res.get('metadata')}")
            exit() # テストを終了

        documents = documents_res["results"]
        print(f"取得件数: {len(documents)}件")

        # --- 書類ダウンロードテスト ---
        # 有価証券報告書 (docTypeCode: 120) を探す
        target_doc = None
        for doc in documents:
            if doc.get("docTypeCode") == "120": # xbrlFlagのチェックは一旦外す
                target_doc = doc
                break
        
        if not target_doc:
            print("\n本日のリストに有価証券報告書(docTypeCode: 120)が見つかりませんでした。")
            exit()

        test_doc_id = target_doc['docID']
        filer_name = target_doc['filerName']
        save_dir = "temp_downloads"
        os.makedirs(save_dir, exist_ok=True)
        
        print(f"\n--- 書類ダウンロードテスト ---")
        print(f"有価証券報告書を見つけました: {filer_name} (docID: {test_doc_id})")

        # まず type=1 (提出本文書) のダウンロードを試す
        main_doc_save_path = os.path.join(save_dir, f"{test_doc_id}_main.zip")
        print(f"提出本文書 (type=1) をダウンロードします...")
        success_main_doc = api.download_document(test_doc_id, save_path=main_doc_save_path, type=1)
        if success_main_doc:
            print(f"提出本文書ダウンロード成功。ファイルサイズ: {os.path.getsize(main_doc_save_path)} bytes")
        else:
            print("提出本文書ダウンロード失敗。")

        # 次に type=5 (XBRL) のダウンロードを試す
        xbrl_doc_save_path = os.path.join(save_dir, f"{test_doc_id}_xbrl.zip")
        print(f"XBRLデータ (type=5) をダウンロードします...")
        success_xbrl_doc = api.download_document(test_doc_id, save_path=xbrl_doc_save_path, type=5)
        if success_xbrl_doc:
            print(f"XBRLデータダウンロード成功。ファイルサイズ: {os.path.getsize(xbrl_doc_save_path)} bytes")
        else:
            print("XBRLデータダウンロード失敗。")

    except ValueError as e:
        print(e)
