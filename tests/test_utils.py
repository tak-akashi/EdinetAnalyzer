import pytest
import os
import tempfile
import shutil
import zipfile
import pandas as pd
from pathlib import Path


class TestHelpers:
    """テスト用ヘルパー関数のクラス"""
    
    @staticmethod
    def create_sample_xbrl_zip(temp_dir: str, filename: str = "sample.zip") -> str:
        """サンプルXBRL ZIPファイルを作成する"""
        # サンプルCSVデータ
        sample_data = {
            "要素ID": [
                "jppfs_cor:CallLoansCAFND",
                "jppfs_cor:SecurityInvestmentTrustBeneficiarySecuritiesCAFND", 
                "jppfs_cor:Assets",
                "jppfs_cor:NetAssets"
            ],
            "項目名": [
                "コール・ローン",
                "投資信託受益証券",
                "資産合計",
                "純資産"
            ],
            "値": [500000000, 10000000000, 10500000000, 10000000000],
            "コンテキストID": ["ctx1", "ctx2", "ctx3", "ctx4"],
            "相対年度": ["当期", "当期", "当期", "当期"],
            "連結・個別": ["個別", "個別", "個別", "個別"],
            "期間・時点": ["時点", "時点", "時点", "時点"],
            "ユニットID": ["unit1", "unit1", "unit1", "unit1"],
            "単位": ["円", "円", "円", "円"]
        }
        
        # CSVファイル作成
        df = pd.DataFrame(sample_data)
        csv_file = os.path.join(temp_dir, "sample_data.csv")
        df.to_csv(csv_file, index=False, encoding="utf-16", sep="\t")
        
        # ZIPファイル作成
        zip_path = os.path.join(temp_dir, filename)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # EDINET XBRL-CSVの標準的なディレクトリ構造
            zf.write(csv_file, "XBRL_TO_CSV/sample_data.csv")
        
        # 一時CSVファイルを削除
        os.remove(csv_file)
        
        return zip_path
    
    @staticmethod
    def create_corrupt_zip(temp_dir: str, filename: str = "corrupt.zip") -> str:
        """破損したZIPファイルを作成する"""
        corrupt_zip = os.path.join(temp_dir, filename)
        with open(corrupt_zip, "w") as f:
            f.write("This is not a valid ZIP file content")
        return corrupt_zip
    
    @staticmethod
    def create_empty_zip(temp_dir: str, filename: str = "empty.zip") -> str:
        """空のZIPファイルを作成する"""
        empty_zip = os.path.join(temp_dir, filename)
        with zipfile.ZipFile(empty_zip, 'w') as zf:
            pass  # 何も追加しない
        return empty_zip
    
    @staticmethod
    def create_multi_company_edinet_response():
        """複数企業を含むEDINET APIレスポンスを作成する"""
        return {
            "metadata": {
                "title": "EDINET提出書類一覧API",
                "parameter": {"date": "2024-07-10", "type": 2},
                "resultset": {"count": 3},
                "processDateTime": "2024-07-10T15:00:00+09:00",
                "status": "OK",
                "message": ""
            },
            "results": [
                {
                    "seqNumber": 1,
                    "docID": "S100001",
                    "edinetCode": "E12345",
                    "filerName": "楽天グループ株式会社",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2024-07-10T15:00:00",
                    "xbrlFlag": "1",
                    "pdfFlag": "1"
                },
                {
                    "seqNumber": 2,
                    "docID": "S100002",
                    "edinetCode": "E54321",
                    "filerName": "ソフトバンクグループ株式会社",
                    "docDescription": "四半期報告書",
                    "submitDateTime": "2024-07-10T16:00:00",
                    "xbrlFlag": "1",
                    "pdfFlag": "1"
                },
                {
                    "seqNumber": 3,
                    "docID": "S100003",
                    "edinetCode": "E98765",
                    "filerName": "トヨタ自動車株式会社",
                    "docDescription": "有価証券報告書",
                    "submitDateTime": "2024-07-10T17:00:00",
                    "xbrlFlag": "1",
                    "pdfFlag": "1"
                }
            ]
        }
    
    @staticmethod
    def assert_json_structure(json_str: str, required_keys: list):
        """JSON文字列が必要なキーを含んでいることを確認する"""
        import json
        data = json.loads(json_str)
        for key in required_keys:
            assert key in data, f"Required key '{key}' not found in JSON"
        return data
    
    @staticmethod
    def assert_financial_data_structure(financial_data: dict):
        """財務データの構造が正しいことを確認する"""
        assert isinstance(financial_data, dict)
        
        for item_name, item_data in financial_data.items():
            assert isinstance(item_data, dict), f"Item {item_name} is not a dict"
            assert "value" in item_data, f"Item {item_name} missing 'value'"
            assert "display_name" in item_data, f"Item {item_name} missing 'display_name'"
            assert isinstance(item_data["value"], (int, float)), f"Item {item_name} value is not numeric"
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """関数の実行時間を測定する"""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time
    
    @staticmethod
    def measure_memory_usage(func, *args, **kwargs):
        """関数のメモリ使用量を測定する"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        result = func(*args, **kwargs)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        return result, memory_increase


class TestDataGenerator:
    """テストデータ生成用のクラス"""
    
    @staticmethod
    def generate_xbrl_data(num_records: int = 100, company_type: str = "investment_trust"):
        """指定された件数のXBRLデータを生成する"""
        import random
        
        if company_type == "investment_trust":
            base_elements = [
                "jppfs_cor:CallLoansCAFND",
                "jppfs_cor:SecurityInvestmentTrustBeneficiarySecuritiesCAFND",
                "jppfs_cor:Assets",
                "jppfs_cor:NetAssets"
            ]
            base_names = [
                "コール・ローン",
                "投資信託受益証券",
                "資産合計",
                "純資産"
            ]
        else:  # general_company
            base_elements = [
                "jpcrp_cor:NetSales",
                "jpcrp_cor:OperatingIncome",
                "jpcrp_cor:OrdinaryIncome",
                "jpcrp_cor:Assets"
            ]
            base_names = [
                "売上高",
                "営業利益",
                "経常利益",
                "資産合計"
            ]
        
        data = []
        for i in range(num_records):
            element_idx = i % len(base_elements)
            data.append({
                "要素ID": f"{base_elements[element_idx]}_{i}",
                "項目名": f"{base_names[element_idx]}{i}",
                "値": random.randint(1000000, 1000000000),
                "コンテキストID": f"ctx{i % 10}",
                "相対年度": random.choice(["当期", "前期"]),
                "連結・個別": random.choice(["連結", "個別"]),
                "期間・時点": random.choice(["期間", "時点"]),
                "ユニットID": "JPY",
                "単位": "円"
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def generate_edinet_documents(num_docs: int = 10):
        """指定された件数のEDINET書類データを生成する"""
        import random
        from datetime import datetime, timedelta
        
        companies = [
            "楽天グループ", "ソフトバンクグループ", "トヨタ自動車", 
            "NTTドコモ", "KDDI", "三菱UFJ", "三井住友", "みずほ",
            "野村證券", "大和証券"
        ]
        
        doc_types = ["有価証券報告書", "四半期報告書", "半期報告書"]
        
        documents = []
        base_date = datetime(2024, 7, 10)
        
        for i in range(num_docs):
            submit_date = base_date - timedelta(days=random.randint(0, 30))
            
            documents.append({
                "docID": f"S{100000 + i:06d}",
                "edinetCode": f"E{random.randint(10000, 99999)}",
                "filerName": f"{random.choice(companies)}株式会社",
                "docDescription": random.choice(doc_types),
                "submitDateTime": submit_date.isoformat(),
                "xbrlFlag": "1",
                "pdfFlag": "1",
                "disclosureStatus": "0"
            })
        
        return {
            "metadata": {
                "title": "EDINET提出書類一覧API",
                "resultset": {"count": len(documents)},
                "status": "OK"
            },
            "results": documents
        }


class TestValidators:
    """テスト結果検証用のクラス"""
    
    @staticmethod
    def validate_langchain_tool_result(result_json: str, tool_name: str):
        """LangChainツールの結果を検証する"""
        import json
        
        data = json.loads(result_json)
        
        # 基本的な構造確認
        assert "success" in data, f"Tool {tool_name} result missing 'success' field"
        
        if data["success"]:
            # 成功時の追加フィールド確認
            if tool_name == "edinet_search":
                required_fields = ["company_name", "total_found", "documents"]
            elif tool_name == "edinet_download":
                required_fields = ["doc_id", "document_type", "file_path"]
            elif tool_name == "xbrl_analysis":
                required_fields = ["analysis_type", "company_type"]
            else:
                required_fields = []
            
            for field in required_fields:
                assert field in data, f"Tool {tool_name} success result missing '{field}'"
        else:
            # 失敗時はエラー情報が含まれていることを確認
            assert "error" in data or "message" in data, f"Tool {tool_name} failure result missing error info"
        
        return data
    
    @staticmethod
    def validate_xbrl_analysis_result(result_data: dict):
        """XBRL解析結果を検証する"""
        if result_data["success"]:
            assert "company_type" in result_data
            assert "analysis_type" in result_data
            
            if "financial_data" in result_data:
                TestHelpers.assert_financial_data_structure(result_data["financial_data"])
            
            if "total_elements" in result_data:
                assert isinstance(result_data["total_elements"], int)
                assert result_data["total_elements"] >= 0
    
    @staticmethod
    def validate_performance_metrics(execution_time: float, memory_increase: int,
                                   max_time: float = 30.0, max_memory_mb: int = 100):
        """パフォーマンス指標を検証する"""
        assert execution_time < max_time, f"Execution time {execution_time:.2f}s exceeds limit {max_time}s"
        
        memory_mb = memory_increase / (1024 * 1024)
        assert memory_mb < max_memory_mb, f"Memory increase {memory_mb:.2f}MB exceeds limit {max_memory_mb}MB"


@pytest.fixture
def test_helpers():
    """テストヘルパーのフィクスチャ"""
    return TestHelpers


@pytest.fixture
def data_generator():
    """データ生成器のフィクスチャ"""
    return TestDataGenerator


@pytest.fixture
def validators():
    """バリデーターのフィクスチャ"""
    return TestValidators


@pytest.fixture
def sample_xbrl_zip(temp_dir, test_helpers):
    """サンプルXBRL ZIPファイルのフィクスチャ"""
    return test_helpers.create_sample_xbrl_zip(temp_dir)


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""
    
    def test_create_sample_xbrl_zip(self, temp_dir, test_helpers):
        """サンプルXBRL ZIP作成のテスト"""
        zip_path = test_helpers.create_sample_xbrl_zip(temp_dir, "test_sample.zip")
        
        assert os.path.exists(zip_path)
        
        # ZIP内容の確認
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            assert "XBRL_TO_CSV/sample_data.csv" in file_list
    
    def test_create_corrupt_zip(self, temp_dir, test_helpers):
        """破損ZIP作成のテスト"""
        corrupt_path = test_helpers.create_corrupt_zip(temp_dir)
        
        assert os.path.exists(corrupt_path)
        
        # ZIPとして読めないことを確認
        with pytest.raises(zipfile.BadZipFile):
            with zipfile.ZipFile(corrupt_path, 'r'):
                pass
    
    def test_json_structure_assertion(self, test_helpers):
        """JSON構造確認のテスト"""
        test_json = '{"success": true, "data": {"value": 123}}'
        
        # 正常ケース
        data = test_helpers.assert_json_structure(test_json, ["success", "data"])
        assert data["success"] is True
        
        # 異常ケース
        with pytest.raises(AssertionError):
            test_helpers.assert_json_structure(test_json, ["success", "missing_key"])
    
    def test_execution_time_measurement(self, test_helpers):
        """実行時間測定のテスト"""
        import time
        
        def slow_function():
            time.sleep(0.1)
            return "result"
        
        result, execution_time = test_helpers.measure_execution_time(slow_function)
        
        assert result == "result"
        assert execution_time >= 0.1
        assert execution_time < 0.2  # 合理的な上限
    
    def test_data_generator_xbrl(self, data_generator):
        """XBRLデータ生成のテスト"""
        # 投資信託データ
        it_data = data_generator.generate_xbrl_data(50, "investment_trust")
        assert len(it_data) == 50
        assert "要素ID" in it_data.columns
        assert any("jppfs_cor:" in str(elem) for elem in it_data["要素ID"])
        
        # 一般企業データ
        gc_data = data_generator.generate_xbrl_data(30, "general_company")
        assert len(gc_data) == 30
        assert any("jpcrp_cor:" in str(elem) for elem in gc_data["要素ID"])
    
    def test_data_generator_edinet(self, data_generator):
        """EDINETデータ生成のテスト"""
        edinet_data = data_generator.generate_edinet_documents(5)
        
        assert "metadata" in edinet_data
        assert "results" in edinet_data
        assert len(edinet_data["results"]) == 5
        
        for doc in edinet_data["results"]:
            assert "docID" in doc
            assert "filerName" in doc
            assert "docDescription" in doc
    
    def test_validators_langchain_tool(self, validators):
        """LangChainツール結果検証のテスト"""
        # 成功ケース
        success_json = '{"success": true, "company_name": "test", "total_found": 1, "documents": []}'
        result = validators.validate_langchain_tool_result(success_json, "edinet_search")
        assert result["success"] is True
        
        # 失敗ケース
        failure_json = '{"success": false, "error": "test error"}'
        result = validators.validate_langchain_tool_result(failure_json, "edinet_search")
        assert result["success"] is False
    
    def test_validators_performance(self, validators):
        """パフォーマンス検証のテスト"""
        # 正常ケース
        validators.validate_performance_metrics(1.0, 10 * 1024 * 1024)  # 1秒, 10MB
        
        # 時間超過ケース
        with pytest.raises(AssertionError):
            validators.validate_performance_metrics(35.0, 10 * 1024 * 1024, max_time=30.0)
        
        # メモリ超過ケース
        with pytest.raises(AssertionError):
            validators.validate_performance_metrics(1.0, 150 * 1024 * 1024, max_memory_mb=100)