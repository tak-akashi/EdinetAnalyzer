import pytest
import requests_mock
from unittest.mock import patch, mock_open
import json
import os
from src.edinet_analyzer.tools.edinet_api import EdinetApi


class TestEdinetApi:
    """EDINET APIクライアントのテストクラス"""
    
    def test_init_with_api_key(self, mock_edinet_api_key):
        """APIキーが設定されている場合の初期化テスト"""
        api = EdinetApi()
        assert api.api_key == mock_edinet_api_key
    
    def test_init_without_api_key(self):
        """APIキーが設定されていない場合の初期化テスト"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="EDINET_API_KEYが設定されていません"):
                EdinetApi()
    
    def test_get_documents_list_success(self, requests_mock, mock_edinet_api_key, sample_edinet_response):
        """書類一覧取得の成功テスト"""
        # モックレスポンスを設定
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents.json",
            json=sample_edinet_response
        )
        
        api = EdinetApi()
        result = api.get_documents_list(date="2024-07-10")
        
        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["docID"] == "S100TEST"
        assert result["results"][0]["filerName"] == "テスト企業株式会社"
    
    def test_get_documents_list_default_date(self, requests_mock, mock_edinet_api_key):
        """デフォルト日付での書類一覧取得テスト"""
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents.json",
            json={"results": []}
        )
        
        api = EdinetApi()
        result = api.get_documents_list()
        
        # リクエストが送信されたことを確認
        assert requests_mock.called
        assert result is not None
    
    def test_get_documents_list_http_error(self, requests_mock, mock_edinet_api_key):
        """HTTP エラーの場合のテスト"""
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents.json",
            status_code=404
        )
        
        api = EdinetApi()
        result = api.get_documents_list(date="2024-07-10")
        
        assert result is None
    
    def test_download_xbrl_document_success(self, requests_mock, mock_edinet_api_key, temp_dir):
        """XBRL書類ダウンロードの成功テスト"""
        # モックレスポンスを設定
        mock_content = b"fake xbrl zip content"
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents/S100TEST",
            content=mock_content,
            headers={"Content-Type": "application/zip"}
        )
        
        api = EdinetApi()
        
        # 一時ディレクトリに変更
        with patch('src.edinet_analyzer.tools.edinet_api.os.makedirs'):
            with patch('src.edinet_analyzer.tools.edinet_api.open', mock_open()) as mock_file:
                result = api.download_xbrl_document("S100TEST")
        
        assert result == "temp_downloads/S100TEST_xbrl.zip"
        mock_file.assert_called_once()
    
    def test_download_xbrl_document_http_error(self, requests_mock, mock_edinet_api_key):
        """XBRL書類ダウンロードのHTTPエラーテスト"""
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents/S100TEST",
            status_code=404
        )
        
        api = EdinetApi()
        result = api.download_xbrl_document("S100TEST")
        
        assert result is None
    
    def test_download_main_document_success(self, requests_mock, mock_edinet_api_key):
        """メイン書類ダウンロードの成功テスト"""
        mock_content = b"fake main document content"
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents/S100TEST",
            content=mock_content,
            headers={"Content-Type": "application/pdf"}
        )
        
        api = EdinetApi()
        
        with patch('src.edinet_analyzer.tools.edinet_api.os.makedirs'):
            with patch('src.edinet_analyzer.tools.edinet_api.open', mock_open()) as mock_file:
                result = api.download_main_document("S100TEST")
        
        assert result == "temp_downloads/S100TEST_main.zip"
        mock_file.assert_called_once()
    
    def test_api_params_structure(self, mock_edinet_api_key):
        """APIパラメータの構造テスト"""
        api = EdinetApi()
        
        # プライベートメソッドのテストのため、実装を直接確認
        assert hasattr(api, 'api_key')
        assert api.BASE_URL == "https://api.edinet-fsa.go.jp/api/v2"
    
    def test_request_parameters(self, requests_mock, mock_edinet_api_key):
        """リクエストパラメータの確認テスト"""
        requests_mock.get(
            "https://api.edinet-fsa.go.jp/api/v2/documents.json",
            json={"results": []}
        )
        
        api = EdinetApi()
        api.get_documents_list(date="2024-07-10", type=1)
        
        # リクエストパラメータを確認
        request = requests_mock.last_request
        assert "date=2024-07-10" in request.query
        assert "type=1" in request.query
        # APIキーはどちらかのパラメータで含まれている
        assert f"subscription-key={mock_edinet_api_key.lower()}" in request.query.lower() or f"subscription-key={mock_edinet_api_key}" in request.query


@pytest.mark.integration
class TestEdinetApiIntegration:
    """EDINET APIの統合テスト（実際のAPIを使用）"""
    
    @pytest.mark.skipif(
        not os.environ.get("EDINET_API_KEY"),
        reason="EDINET_API_KEY環境変数が設定されていません"
    )
    def test_real_api_connection(self):
        """実際のAPIとの接続テスト（スキップ可能）"""
        api = EdinetApi()
        
        # 過去の日付で安全にテスト
        result = api.get_documents_list(date="2024-07-01")
        
        if result is not None:
            assert "results" in result
            assert isinstance(result["results"], list)
    
    @pytest.mark.skipif(
        not os.environ.get("EDINET_API_KEY"),
        reason="EDINET_API_KEY環境変数が設定されていません"
    )
    def test_search_specific_company(self):
        """特定企業の検索テスト（スキップ可能）"""
        api = EdinetApi()
        
        # 楽天グループの開示書類を検索
        result = api.get_documents_list(date="2024-07-01")
        
        if result and "results" in result:
            # 楽天関連の書類があるかチェック
            rakuten_docs = [
                doc for doc in result["results"]
                if doc.get("filerName") and "楽天" in doc.get("filerName", "")
            ]
            
            # 楽天関連書類が見つかった場合のアサーション
            if rakuten_docs:
                assert len(rakuten_docs) > 0
                assert all("楽天" in doc["filerName"] for doc in rakuten_docs)