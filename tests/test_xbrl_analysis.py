import pytest
import pandas as pd
import tempfile
import zipfile
import os
from unittest.mock import patch, MagicMock
from src.edinet_analyzer.tools.enhanced_xbrl_parser import EnhancedXbrlParser
from src.edinet_analyzer.tools.financial_mapping import FinancialMapping
from src.edinet_analyzer.tools.financial_extractor import FinancialExtractor
from src.edinet_analyzer.tools.taxonomy_analyzer import TaxonomyAnalyzer


class TestFinancialMapping:
    """財務マッピング設定のテストクラス"""
    
    def test_init(self):
        """初期化テスト"""
        mapping = FinancialMapping()
        assert isinstance(mapping.mappings, dict)
        assert "investment_trust" in mapping.mappings
        assert "general_company" in mapping.mappings
    
    def test_get_mapping_for_company_type(self):
        """企業タイプ別マッピング取得テスト"""
        mapping = FinancialMapping()
        
        # 投資信託のマッピング取得
        it_mapping = mapping.get_mapping_for_company_type("investment_trust")
        assert "call_loans" in it_mapping
        assert "total_assets" in it_mapping
        
        # 一般企業のマッピング取得
        gc_mapping = mapping.get_mapping_for_company_type("general_company")
        assert "net_sales" in gc_mapping
        assert "operating_income" in gc_mapping
        
        # 存在しない企業タイプ
        unknown_mapping = mapping.get_mapping_for_company_type("unknown_type")
        assert unknown_mapping == {}
    
    def test_get_element_ids_for_item(self):
        """財務項目の要素ID取得テスト"""
        mapping = FinancialMapping()
        
        # 投資信託のコール・ローン
        element_ids = mapping.get_element_ids_for_item("investment_trust", "call_loans")
        assert "jppfs_cor:CallLoansCAFND" in element_ids
        
        # 存在しない項目
        empty_ids = mapping.get_element_ids_for_item("investment_trust", "non_existent")
        assert empty_ids == []
    
    def test_add_custom_mapping(self):
        """カスタムマッピング追加テスト"""
        mapping = FinancialMapping()
        
        mapping.add_custom_mapping(
            "custom_type", 
            "custom_item",
            ["custom:element1", "custom:element2"],
            "カスタム項目"
        )
        
        custom_mapping = mapping.get_mapping_for_company_type("custom_type")
        assert "custom_item" in custom_mapping
        assert custom_mapping["custom_item"]["display_name"] == "カスタム項目"


class TestFinancialExtractor:
    """財務データ抽出器のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mapping = FinancialMapping()
        self.extractor = FinancialExtractor(self.mapping)
    
    def test_init(self):
        """初期化テスト"""
        assert self.extractor.mapping_config == self.mapping
    
    def test_extract_financial_data_empty_df(self):
        """空のDataFrameでの抽出テスト"""
        empty_df = pd.DataFrame()
        result = self.extractor.extract_financial_data(empty_df, "investment_trust")
        assert result == {}
    
    def test_extract_financial_data_missing_columns(self):
        """必要なカラムが欠けているDataFrameでの抽出テスト"""
        df = pd.DataFrame({"dummy_column": [1, 2, 3]})
        result = self.extractor.extract_financial_data(df, "investment_trust")
        assert result == {}
    
    def test_extract_financial_data_investment_trust(self):
        """投資信託データの抽出テスト"""
        # テスト用のDataFrameを作成
        test_data = {
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
            "値": [689477430.0, 66922526895.0, 67708176982.0, 67196000625.0],
            "コンテキストID": ["ctx1", "ctx2", "ctx3", "ctx4"],
            "相対年度": ["当期", "当期", "当期", "当期"]
        }
        df = pd.DataFrame(test_data)
        
        result = self.extractor.extract_financial_data(df, "investment_trust")
        
        assert "call_loans" in result
        assert result["call_loans"]["value"] == 689477430.0
        assert result["call_loans"]["display_name"] == "コール・ローン"
    
    def test_search_available_elements(self):
        """利用可能要素の検索テスト"""
        test_data = {
            "要素ID": [
                "jppfs_cor:Assets",
                "jppfs_cor:CallLoans",
                "jppfs_cor:NetIncome"
            ],
            "項目名": [
                "資産合計",
                "コール・ローン",
                "当期純利益"
            ],
            "値": [1000000, 500000, 200000]
        }
        df = pd.DataFrame(test_data)
        
        # "資産"で検索
        result = self.extractor.search_available_elements(df, ["資産"])
        assert not result.empty
        assert "資産" in result["項目名"].iloc[0]
    
    def test_generate_summary_report(self, sample_financial_data):
        """サマリーレポート生成テスト"""
        report = self.extractor.generate_summary_report(
            sample_financial_data, "investment_trust"
        )
        
        assert "投資信託" in report
        assert "コール・ローン" in report
        assert "億円" in report
    
    def test_export_to_dataframe(self, sample_financial_data):
        """DataFrame出力テスト"""
        df = self.extractor.export_to_dataframe(sample_financial_data)
        
        assert not df.empty
        assert "item_name" in df.columns
        assert "display_name" in df.columns
        assert "value" in df.columns
        assert len(df) == len(sample_financial_data)


class TestTaxonomyAnalyzer:
    """タクソノミ分析器のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.analyzer = TaxonomyAnalyzer()
    
    def test_init(self):
        """初期化テスト"""
        assert hasattr(self.analyzer, 'company_types')
        assert "investment_trust" in self.analyzer.company_types
        assert "general_company" in self.analyzer.company_types
    
    def test_detect_company_type_investment_trust(self):
        """投資信託企業タイプ判別テスト"""
        elements = [
            "jppfs_cor:CallLoansCAFND",
            "jppfs_cor:SecurityInvestmentTrustBeneficiarySecuritiesCAFND",
            "jppfs_cor:Assets"
        ]
        
        company_type = self.analyzer._detect_company_type(elements)
        assert company_type == "investment_trust"
    
    def test_detect_company_type_general_company(self):
        """一般企業タイプ判別テスト"""
        elements = [
            "jpcrp_cor:NetSales",
            "jpcrp_cor:OperatingIncome",
            "jpcrp_cor:Assets"
        ]
        
        company_type = self.analyzer._detect_company_type(elements)
        assert company_type == "general_company"
    
    def test_detect_company_type_unknown(self):
        """不明企業タイプ判別テスト"""
        elements = [
            "unknown:Element1",
            "unknown:Element2"
        ]
        
        company_type = self.analyzer._detect_company_type(elements)
        assert company_type == "unknown"
    
    def test_analyze_prefixes(self):
        """プレフィックス分析テスト"""
        elements = [
            "jppfs_cor:Element1",
            "jppfs_cor:Element2",
            "jpcrp_cor:Element3",
            "other:Element4"
        ]
        
        prefixes = self.analyzer._analyze_prefixes(elements)
        assert "jppfs_cor:" in prefixes
        assert "jpcrp_cor:" in prefixes
        assert prefixes["jppfs_cor:"] == 2
        assert prefixes["jpcrp_cor:"] == 1
    
    def test_extract_financial_candidates(self):
        """財務項目候補抽出テスト"""
        elements = [
            "jppfs_cor:Assets",
            "jppfs_cor:NetAssets", 
            "jppfs_cor:CallLoans",
            "jpcrp_cor:NetSales"
        ]
        
        # 投資信託として分析
        candidates = self.analyzer._extract_financial_candidates(elements, "investment_trust")
        assert "assets" in candidates
        assert len(candidates["assets"]) > 0
        
        # 一般企業として分析
        candidates = self.analyzer._extract_financial_candidates(elements, "general_company")
        assert "sales" in candidates


class TestEnhancedXbrlParser:
    """拡張XBRL解析器のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.parser = EnhancedXbrlParser()
    
    def test_init(self):
        """初期化テスト"""
        assert hasattr(self.parser, 'taxonomy_analyzer')
        assert hasattr(self.parser, 'financial_mapping')
        assert hasattr(self.parser, 'financial_extractor')
    
    def test_extract_xbrl_data_file_not_found(self):
        """存在しないファイルでの解析テスト"""
        result = self.parser.extract_xbrl_data("non_existent_file.zip")
        assert result is None
    
    @pytest.mark.skipif(
        not os.path.exists("temp_downloads/S100VVBR_xbrl.zip"),
        reason="サンプルXBRLファイルが見つかりません"
    )
    def test_extract_xbrl_data_sample_file(self, sample_xbrl_file):
        """サンプルファイルでの解析テスト"""
        result = self.parser.extract_xbrl_data(sample_xbrl_file)
        
        if result:
            assert "company_type" in result
            assert "financial_data" in result
            assert "total_elements" in result
            assert isinstance(result["financial_data"], dict)
    
    def test_detect_company_type_empty_data(self):
        """空データでの企業タイプ判別テスト"""
        # 空のDataFrameを設定
        self.parser.combined_df = pd.DataFrame()
        company_type = self.parser._detect_company_type()
        assert company_type == "unknown"
    
    def test_detect_company_type_missing_column(self):
        """要素IDカラムが存在しない場合のテスト"""
        # 要素IDカラムのないDataFrameを設定
        self.parser.combined_df = pd.DataFrame({"dummy": [1, 2, 3]})
        company_type = self.parser._detect_company_type()
        assert company_type == "unknown"
    
    def test_get_financial_summary_no_result(self):
        """結果がない場合の財務サマリーテスト"""
        summary = self.parser.get_financial_summary()
        assert summary.empty
    
    def test_search_financial_items_no_data(self):
        """データがない場合の検索テスト"""
        result = self.parser.search_financial_items(["資産"])
        assert result.empty
    
    def test_get_detailed_analysis_no_result(self):
        """結果がない場合の詳細分析テスト"""
        analysis = self.parser.get_detailed_analysis()
        assert "データが読み込まれていません" in analysis
    
    def test_export_to_csv_no_data(self, temp_dir):
        """データがない場合のCSV出力テスト"""
        output_file = os.path.join(temp_dir, "test_output.csv")
        
        with patch('builtins.print') as mock_print:
            self.parser.export_to_csv(output_file)
            mock_print.assert_called_with("出力する財務データがありません。")


@pytest.mark.integration
class TestXbrlAnalysisIntegration:
    """XBRL解析の統合テスト"""
    
    @pytest.mark.skipif(
        not os.path.exists("temp_downloads/S100VVBR_xbrl.zip"),
        reason="サンプルXBRLファイルが見つかりません"
    )
    def test_full_analysis_pipeline(self, sample_xbrl_file, temp_dir):
        """完全な解析パイプラインのテスト"""
        parser = EnhancedXbrlParser()
        
        # 解析実行
        result = parser.extract_xbrl_data(sample_xbrl_file)
        
        if result:
            # 基本的な結果構造の確認
            assert "company_type" in result
            assert "financial_data" in result
            assert "total_elements" in result
            
            # 詳細分析の実行
            detailed_analysis = parser.get_detailed_analysis()
            assert len(detailed_analysis) > 0
            
            # DataFrame変換の確認
            df_summary = parser.get_financial_summary()
            if not df_summary.empty:
                assert "item_name" in df_summary.columns
                assert "display_name" in df_summary.columns
                assert "value" in df_summary.columns
            
            # CSV出力の確認
            output_file = os.path.join(temp_dir, "integration_test.csv")
            parser.export_to_csv(output_file)
            
            # 検索機能の確認
            search_result = parser.search_financial_items(["資産"])
            assert isinstance(search_result, pd.DataFrame)
    
    def test_error_handling_corrupt_zip(self, temp_dir):
        """破損したZIPファイルのエラーハンドリングテスト"""
        # 破損したZIPファイルを作成
        corrupt_zip = os.path.join(temp_dir, "corrupt.zip")
        with open(corrupt_zip, "w") as f:
            f.write("This is not a valid zip file")
        
        parser = EnhancedXbrlParser()
        result = parser.extract_xbrl_data(corrupt_zip)
        
        assert result is None