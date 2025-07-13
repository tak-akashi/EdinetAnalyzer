import json

class FinancialMapping:
    """
    企業タイプ別の財務項目マッピング設定を管理するクラス
    """
    
    def __init__(self):
        self.mappings = {
            "investment_trust": {
                "call_loans": {
                    "element_ids": ["jppfs_cor:CallLoansCAFND"],
                    "display_name": "コール・ローン",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["NonConsolidatedMember"]
                },
                "investment_securities": {
                    "element_ids": [
                        "jppfs_cor:SecurityInvestmentTrustBeneficiarySecuritiesCAFND",
                        "jppfs_cor:SecurityInvestmentTrustBeneficiarySecuritiesCA"
                    ],
                    "display_name": "投資信託受益証券",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["NonConsolidatedMember"]
                },
                "total_assets": {
                    "element_ids": ["jppfs_cor:Assets", "jppfs_cor:TotalAssets"],
                    "display_name": "資産合計",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["NonConsolidatedMember"]
                },
                "net_assets": {
                    "element_ids": ["jppfs_cor:NetAssets", "jppfs_cor:Equity"],
                    "display_name": "純資産",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["NonConsolidatedMember"]
                },
                "profit_loss_securities": {
                    "element_ids": ["jppfs_cor:ProfitAndLossOnBuyingAndSellingOfSecuritiesAndOtherOIFND"],
                    "display_name": "有価証券売買損益",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["NonConsolidatedMember"]
                }
            },
            "general_company": {
                "net_sales": {
                    "element_ids": [
                        "jpcrp_cor:NetSales",
                        "jpfr-t-qci:NetSales",
                        "jpcrp_cor:RevenueIFRS"
                    ],
                    "display_name": "売上高",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "operating_income": {
                    "element_ids": [
                        "jpcrp_cor:OperatingIncome",
                        "jpfr-t-qci:OperatingIncome",
                        "jpcrp_cor:OperatingProfitIFRS"
                    ],
                    "display_name": "営業利益",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "ordinary_income": {
                    "element_ids": [
                        "jpcrp_cor:OrdinaryIncome",
                        "jpfr-t-qci:OrdinaryIncome"
                    ],
                    "display_name": "経常利益",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "net_income": {
                    "element_ids": [
                        "jpcrp_cor:ProfitLoss",
                        "jpfr-t-qci:ProfitLoss",
                        "jpcrp_cor:ProfitLossAttributableToOwnersOfParent",
                        "jpcrp_cor:NetIncome"
                    ],
                    "display_name": "当期純利益",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "total_assets": {
                    "element_ids": [
                        "jpcrp_cor:Assets",
                        "jpfr-t-qci:Assets",
                        "jpcrp_cor:TotalAssets"
                    ],
                    "display_name": "資産合計",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "total_liabilities": {
                    "element_ids": [
                        "jpcrp_cor:Liabilities",
                        "jpfr-t-qci:Liabilities",
                        "jpcrp_cor:TotalLiabilities"
                    ],
                    "display_name": "負債合計",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "net_assets": {
                    "element_ids": [
                        "jpcrp_cor:NetAssets",
                        "jpfr-t-qci:NetAssets",
                        "jpcrp_cor:Equity"
                    ],
                    "display_name": "純資産合計",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                }
            },
            "bank": {
                "ordinary_income": {
                    "element_ids": ["jpbank_cor:OrdinaryIncome"],
                    "display_name": "経常利益",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "ordinary_business_profit": {
                    "element_ids": ["jpbank_cor:OrdinaryBusinessProfit"],
                    "display_name": "業務純益",
                    "context_priority": ["CurrentYearDuration", "Prior1YearDuration"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                },
                "total_assets": {
                    "element_ids": ["jpbank_cor:Assets"],
                    "display_name": "資産の部合計",
                    "context_priority": ["CurrentYearInstant", "Prior1YearInstant"],
                    "member_priority": ["ConsolidatedMember", "NonConsolidatedMember"]
                }
            }
        }
        
        # コンテキストIDのパターン定義
        self.context_patterns = {
            "CurrentYearInstant": ["当期末", "期末"],
            "Prior1YearInstant": ["前期末"],
            "CurrentYearDuration": ["当期", "当連結会計年度"],
            "Prior1YearDuration": ["前期", "前連結会計年度"]
        }
        
        # 連結・個別の優先順位
        self.member_patterns = {
            "ConsolidatedMember": ["連結"],
            "NonConsolidatedMember": ["個別"]
        }
    
    def get_mapping_for_company_type(self, company_type: str):
        """指定された企業タイプのマッピングを取得"""
        return self.mappings.get(company_type, {})
    
    def get_element_ids_for_item(self, company_type: str, item_name: str):
        """特定の財務項目の要素IDリストを取得"""
        mapping = self.get_mapping_for_company_type(company_type)
        item_mapping = mapping.get(item_name, {})
        return item_mapping.get("element_ids", [])
    
    def get_context_priority(self, company_type: str, item_name: str):
        """特定の財務項目のコンテキスト優先順位を取得"""
        mapping = self.get_mapping_for_company_type(company_type)
        item_mapping = mapping.get(item_name, {})
        return item_mapping.get("context_priority", [])
    
    def get_member_priority(self, company_type: str, item_name: str):
        """特定の財務項目のメンバー優先順位を取得"""
        mapping = self.get_mapping_for_company_type(company_type)
        item_mapping = mapping.get(item_name, {})
        return item_mapping.get("member_priority", [])
    
    def add_custom_mapping(self, company_type: str, item_name: str, element_ids: list, 
                          display_name: str, context_priority: list = None, 
                          member_priority: list = None):
        """カスタムマッピングを追加"""
        if company_type not in self.mappings:
            self.mappings[company_type] = {}
        
        self.mappings[company_type][item_name] = {
            "element_ids": element_ids,
            "display_name": display_name,
            "context_priority": context_priority or ["CurrentYearInstant"],
            "member_priority": member_priority or ["NonConsolidatedMember"]
        }
    
    def save_mappings(self, filepath: str):
        """マッピング設定をJSONファイルに保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.mappings, f, ensure_ascii=False, indent=2)
        print(f"マッピング設定を {filepath} に保存しました")
    
    def load_mappings(self, filepath: str):
        """JSONファイルからマッピング設定を読み込み"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.mappings = json.load(f)
            print(f"マッピング設定を {filepath} から読み込みました")
        except FileNotFoundError:
            print(f"マッピングファイルが見つかりません: {filepath}")
        except json.JSONDecodeError:
            print(f"マッピングファイルの形式が不正です: {filepath}")
    
    def print_mappings_summary(self):
        """マッピング設定のサマリーを表示"""
        print("\n=== 財務項目マッピング設定 ===")
        for company_type, items in self.mappings.items():
            print(f"\n[{company_type}]")
            for item_name, config in items.items():
                print(f"  {item_name}: {config['display_name']}")
                print(f"    要素ID: {config['element_ids'][:2]}{'...' if len(config['element_ids']) > 2 else ''}")

if __name__ == '__main__':
    # マッピング設定のテスト
    mapping = FinancialMapping()
    mapping.print_mappings_summary()
    
    # 設定をファイルに保存
    mapping.save_mappings("financial_mappings.json")
    
    # 投資信託用のマッピングテスト
    print("\n=== 投資信託用マッピングテスト ===")
    investment_items = mapping.get_mapping_for_company_type("investment_trust")
    for item_name, config in investment_items.items():
        print(f"{item_name}: {config['display_name']}")
        element_ids = mapping.get_element_ids_for_item("investment_trust", item_name)
        print(f"  要素ID: {element_ids}")