import pytest
import os
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def test_data_dir():
    """テストデータディレクトリのパスを返す"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_xbrl_file():
    """サンプルXBRLファイルのパスを返す"""
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "temp_downloads" / "S100VVBR_xbrl.zip"
    
    if sample_file.exists():
        return str(sample_file)
    else:
        pytest.skip("サンプルXBRLファイルが見つかりません")


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成し、テスト後に削除する"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_edinet_api_key():
    """テスト用のEDINET APIキーを設定する"""
    original_key = os.environ.get("EDINET_API_KEY")
    test_key = "test_api_key_12345"
    os.environ["EDINET_API_KEY"] = test_key
    
    yield test_key
    
    # テスト後に元の値を復元
    if original_key:
        os.environ["EDINET_API_KEY"] = original_key
    else:
        os.environ.pop("EDINET_API_KEY", None)


@pytest.fixture
def sample_financial_data():
    """テスト用の財務データを返す"""
    return {
        "call_loans": {
            "value": 689477430.0,
            "display_name": "コール・ローン",
            "item_name": "call_loans"
        },
        "investment_securities": {
            "value": 66922526895.0,
            "display_name": "投資信託受益証券",
            "item_name": "investment_securities"
        },
        "total_assets": {
            "value": 67708176982.0,
            "display_name": "資産合計",
            "item_name": "total_assets"
        },
        "net_assets": {
            "value": 67196000625.0,
            "display_name": "純資産",
            "item_name": "net_assets"
        }
    }


@pytest.fixture
def sample_edinet_response():
    """テスト用のEDINET API レスポンスを返す"""
    return {
        "metadata": {
            "title": "EDINET提出書類一覧API",
            "parameter": {
                "date": "2024-07-10",
                "type": 2
            },
            "resultset": {
                "count": 2
            },
            "processDateTime": "2024-07-10T15:00:00+09:00",
            "status": "OK",
            "message": ""
        },
        "results": [
            {
                "seqNumber": 1,
                "docID": "S100TEST",
                "edinetCode": "E12345",
                "secCode": "1234",
                "JCN": "1234567890123",
                "filerName": "テスト企業株式会社",
                "fundCode": None,
                "ordinanceCode": "010",
                "formCode": "030000",
                "docTypeCode": "120",
                "periodStart": "2024-04-01",
                "periodEnd": "2024-03-31",
                "submitDateTime": "2024-07-10T15:00:00",
                "docDescription": "有価証券報告書",
                "issuerEdinetCode": None,
                "subjectEdinetCode": None,
                "subsidiaryEdinetCode": None,
                "currentReportReason": None,
                "parentDocID": None,
                "opeDateTime": None,
                "withdrawalStatus": "0",
                "docInfoEditStatus": "0",
                "disclosureStatus": "0",
                "xbrlFlag": "1",
                "pdfFlag": "1",
                "attachDocFlag": "0",
                "englishDocFlag": "0"
            }
        ]
    }