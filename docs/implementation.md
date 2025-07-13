# EDINET分析システム実装ドキュメント

## 概要

EDINET分析システムは、日本の金融庁が提供するEDINETシステムからXBRLデータを取得し、LangGraphを使用してAIエージェントによる自然言語での財務分析を行うシステムです。

### 実装完了ステップ
- ✅ **ステップ1**: EDINET APIクライアント
- ✅ **ステップ2**: XBRL解析モジュール  
- ✅ **ステップ3**: LangChainツール
- ✅ **ステップ4**: LangGraphエージェント
- 🔄 **ステップ5**: StreamlitによるUI（未実装）
- 🔄 **ステップ6**: 全体統合とテスト（未実装）

## システムアーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │───▶│  LangGraph      │───▶│   EDINET API    │
│   (ステップ5)    │    │   Agent         │    │   Client        │
└─────────────────┘    │  (ステップ4)     │    │  (ステップ1)     │
                       └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  LangChain      │    │   XBRL解析      │
                       │   Tools         │    │  モジュール      │
                       │  (ステップ3)     │    │  (ステップ2)     │
                       └─────────────────┘    └─────────────────┘
```

### 主要コンポーネント

1. **EDINET APIクライアント**: 金融庁APIとの通信
2. **XBRL解析モジュール**: 財務データの抽出・分析
3. **LangChainツール**: AIエージェントが使用可能な機能群
4. **LangGraphエージェント**: 自然言語質問応答のワークフロー
5. **StreamlitUI**: ユーザーインターフェース（未実装）

## ステップ別実装詳細

### ステップ1: EDINET APIクライアント

**実装ファイル**: `src/edinet_analyzer/tools/edinet_api.py`

#### 主要機能
- 書類一覧の取得
- XBRLデータのダウンロード
- メインドキュメントのダウンロード

#### 主要クラス
```python
class EdinetApi:
    def __init__(self)
    def get_documents_list(self, date: str = None, type: int = 2)
    def download_xbrl_document(self, doc_id: str)
    def download_main_document(self, doc_id: str)
    def download_document(self, doc_id: str, save_path: str, type: int = 1)
```

#### 使用例
```python
from edinet_analyzer.tools import EdinetApi

api = EdinetApi()
documents = api.get_documents_list(date="2024-07-10")
file_path = api.download_xbrl_document("S100VVBR")
```

### ステップ2: XBRL解析モジュール

**実装ファイル群**:
- `src/edinet_analyzer/tools/enhanced_xbrl_parser.py`
- `src/edinet_analyzer/tools/taxonomy_analyzer.py`
- `src/edinet_analyzer/tools/financial_mapping.py`
- `src/edinet_analyzer/tools/financial_extractor.py`

#### 主要機能
- ZIPファイルの自動展開
- CSVファイルの自動検出・読み込み
- 企業タイプの自動判別（投資信託・一般企業）
- 財務データの抽出・整形
- 検索機能
- レポート生成

#### 主要クラス

**EnhancedXbrlParser**
```python
class EnhancedXbrlParser:
    def extract_xbrl_data(self, zip_file_path: str) -> Optional[Dict[str, Any]]
    def get_financial_summary(self, company_type: str) -> Dict[str, Any]
    def search_financial_items(self, search_terms: List[str]) -> pd.DataFrame
    def export_to_csv(self, output_path: str) -> bool
```

**TaxonomyAnalyzer**
```python
class TaxonomyAnalyzer:
    def detect_company_type(self, elements: List[str]) -> str
    def analyze_prefixes(self, elements: List[str]) -> Dict[str, Any]
    def extract_financial_candidates(self, elements: List[str]) -> List[str]
```

#### 使用例
```python
from edinet_analyzer.tools import EnhancedXbrlParser

parser = EnhancedXbrlParser()
result = parser.extract_xbrl_data("S100VVBR_xbrl.zip")
summary = parser.get_financial_summary("investment_trust")
```

### ステップ3: LangChainツール

**実装ファイル群**:
- `src/edinet_analyzer/langchain_tools/edinet_search_tool.py`
- `src/edinet_analyzer/langchain_tools/xbrl_analysis_tool.py`

#### 実装されたツール

1. **EdinetSearchTool**: EDINET書類検索
2. **EdinetDownloadTool**: 書類ダウンロード
3. **XbrlAnalysisTool**: XBRL解析
4. **XbrlComparisonTool**: XBRL比較分析

#### ツール仕様

**EdinetSearchTool**
```python
# 入力スキーマ
class EdinetSearchInput(BaseModel):
    company_name: str = Field(description="検索対象の企業名")
    date: Optional[str] = Field(description="検索対象日(YYYY-MM-DD)")
    document_type: str = Field(description="書類種別", default="有価証券報告書")

# 使用例
tool = EdinetSearchTool()
result = tool._run("楽天", "2024-07-10", "有価証券報告書")
```

**XbrlAnalysisTool**
```python
# 入力スキーマ
class XbrlAnalysisInput(BaseModel):
    file_path: str = Field(description="XBRLファイルのパス")
    analysis_type: str = Field(description="分析タイプ", default="financial")
    search_terms: Optional[List[str]] = Field(description="検索キーワード")

# 使用例
tool = XbrlAnalysisTool()
result = tool._run("file.zip", "financial")
search_result = tool._run("file.zip", "search", ["資産", "利益"])
```

### ステップ4: LangGraphエージェント

**実装ファイル群**:
- `src/edinet_analyzer/agent.py` - メインエージェント
- `src/edinet_analyzer/state.py` - 状態管理
- `src/edinet_analyzer/nodes.py` - ノード実装
- `src/edinet_analyzer/edges.py` - ルーティングロジック

#### エージェント状態

```python
class EdinetAgentState(TypedDict):
    messages: List[BaseMessage]           # 会話履歴
    query: str                           # ユーザー質問
    company_name: Optional[str]          # 企業名
    search_date: Optional[str]           # 検索日
    document_type: Optional[str]         # 書類種別
    analysis_type: Optional[str]         # 分析タイプ
    search_terms: Optional[List[str]]    # 検索キーワード
    search_results: Optional[List[Dict]] # 検索結果
    downloaded_files: Optional[List[str]] # ダウンロードファイル
    xbrl_analysis: Optional[Dict]        # 解析結果
    final_answer: Optional[str]          # 最終回答
    error_message: Optional[str]         # エラーメッセージ
    retry_count: int                     # リトライ回数
    tool_calls: List[Dict]               # ツール呼び出し履歴
    execution_time: Optional[float]      # 実行時間
    next_action: Optional[str]           # 次アクション
```

#### ワークフローノード

1. **query_analyzer**: 質問解析
   - 企業名、日付、書類種別、分析タイプを抽出
   - LLMを使用してJSON形式で構造化

2. **edinet_search**: EDINET検索
   - EdinetSearchToolを使用して書類検索
   - 企業名でフィルタリング

3. **document_download**: ダウンロード
   - EdinetDownloadToolでXBRLファイル取得
   - エラーハンドリング

4. **xbrl_analysis**: XBRL解析
   - XbrlAnalysisToolで財務データ抽出
   - 分析タイプに応じた処理

5. **answer_generator**: 回答生成
   - LLMで解析結果を自然言語に変換
   - 分かりやすい説明付き

6. **error_handler**: エラー処理
   - リトライ制御
   - エラーメッセージの生成

#### メインエージェントクラス

```python
class EdinetAnalysisAgent:
    def __init__(self, llm: Optional[BaseLLM] = None, enable_memory: bool = True)
    def invoke(self, query: str, config: Optional[Dict] = None) -> Dict[str, Any]
    def stream(self, query: str, config: Optional[Dict] = None)
    def validate_environment(self) -> Dict[str, bool]
    def get_workflow_diagram(self) -> str
```

#### 使用例

```python
from edinet_analyzer import create_agent

# エージェント作成
agent = create_agent(enable_memory=True)

# 質問実行
result = agent.invoke("楽天グループの最新の総資産を教えてください")
print(result["final_answer"])

# ストリーミング実行
for chunk in agent.stream("楽天の財務状況を分析してください"):
    print(chunk)
```

## ファイル構成

```
src/edinet_analyzer/
├── __init__.py                 # パッケージ初期化
├── agent.py                   # メインエージェント
├── state.py                   # 状態管理
├── nodes.py                   # ノード実装
├── edges.py                   # ルーティングロジック
├── app.py                     # Streamlitアプリ（空）
├── tools/                     # 基盤ツール群
│   ├── __init__.py
│   ├── edinet_api.py         # EDINET APIクライアント
│   ├── enhanced_xbrl_parser.py # 高度XBRL解析
│   ├── xbrl_parser.py        # 基本XBRL解析
│   ├── taxonomy_analyzer.py   # タクソノミ分析
│   ├── financial_mapping.py   # 財務データマッピング
│   └── financial_extractor.py # 財務データ抽出
└── langchain_tools/           # LangChainツール
    ├── __init__.py
    ├── edinet_search_tool.py  # EDINET検索ツール
    └── xbrl_analysis_tool.py  # XBRL解析ツール

tests/                         # テストファイル群
├── conftest.py               # テスト設定
├── test_edinet_api.py        # API テスト
├── test_xbrl_analysis.py     # XBRL解析テスト
├── test_langchain_tools.py   # LangChainツールテスト
├── test_integration.py       # 統合テスト
├── test_agent.py             # エージェントテスト
└── test_utils.py             # ユーティリティテスト

docs/                         # ドキュメント
├── plan.md                   # 実装計画
└── implementation.md         # 実装ドキュメント（本ファイル）
```

## 設定と環境変数

### 必須環境変数

```bash
# EDINET API キー
export EDINET_API_KEY="your_edinet_api_key"

# OpenAI API キー（GPT-4o使用時）
export OPENAI_API_KEY="your_openai_api_key"
```

### オプション設定

```python
# エージェント設定例
agent = create_agent(
    model_name="gpt-4o",           # 使用モデル
    enable_memory=True,            # メモリ機能
    api_key="custom_api_key"       # カスタムAPIキー
)
```

## テスト実装

### テストカバレッジ

| モジュール | テストファイル | 主要テスト内容 |
|-----------|---------------|---------------|
| EDINET API | test_edinet_api.py | API通信、エラーハンドリング |
| XBRL解析 | test_xbrl_analysis.py | データ抽出、企業タイプ判別 |
| LangChainツール | test_langchain_tools.py | ツール実行、スキーマ検証 |
| エージェント | test_agent.py | ワークフロー、状態管理 |
| 統合 | test_integration.py | エンドツーエンド |

### テスト実行

```bash
# 全テスト実行
uv run pytest tests/ -v

# 特定テスト実行
uv run pytest tests/test_agent.py -v

# 統合テストのみ
uv run pytest tests/test_integration.py -v -m integration
```

### テスト結果
- **総テスト数**: 81個
- **成功率**: 100% ✅
- **Pydantic v2互換性**: 対応済み ✅

## 使用例

### 基本的な使用方法

```python
import os
from edinet_analyzer import create_agent

# 環境変数設定
os.environ["EDINET_API_KEY"] = "your_key"
os.environ["OPENAI_API_KEY"] = "your_key"

# エージェント作成
agent = create_agent()

# 環境検証
validation = agent.validate_environment()
print("環境検証:", validation)

# 質問実行
queries = [
    "楽天グループの最新の総資産を教えてください",
    "ソフトバンクグループの純利益を調べて",
    "トヨタ自動車の財務状況を分析してください"
]

for query in queries:
    result = agent.invoke(query)
    print(f"質問: {query}")
    print(f"回答: {result['final_answer']}")
    print(f"実行時間: {result['execution_time']:.2f}秒")
    print("-" * 50)
```

### ストリーミング使用例

```python
# リアルタイム処理状況の表示
for chunk in agent.stream("楽天の財務データを分析してください"):
    for node_name, node_data in chunk.items():
        print(f"[{node_name}] 処理中...")
        if "final_answer" in node_data:
            print(f"回答: {node_data['final_answer']}")
```

### メモリ機能使用例

```python
# 会話継続
config = {"configurable": {"thread_id": "user_session_1"}}

result1 = agent.invoke("楽天の総資産を教えて", config=config)
result2 = agent.invoke("それは前年と比べてどうですか？", config=config)  # 文脈を理解

# 履歴取得
history = agent.get_conversation_history("user_session_1")
```

## 今後の実装課題

### ステップ5: StreamlitによるUI

**予定実装内容**:
- ユーザーフレンドリーなWebインターフェース
- リアルタイム処理状況表示
- 結果のグラフィカル表示
- セッション管理

**実装ファイル**:
- `src/edinet_analyzer/app.py`
- `streamlit_config.toml`

### ステップ6: 全体統合とテスト

**予定実装内容**:
- エンドツーエンドテストの拡充
- パフォーマンステスト
- エラーケースの網羅的テスト
- ドキュメントの充実

### 技術的改善点

1. **キャッシュ機能**: 同一書類の重複ダウンロード防止
2. **バッチ処理**: 複数企業の一括分析
3. **可視化機能**: グラフ・チャート生成
4. **データベース連携**: 分析結果の永続化
5. **API拡張**: RESTful API提供

### パフォーマンス最適化

1. **並列処理**: 複数書類の同時処理
2. **メモリ管理**: 大量データ処理時の最適化
3. **ネットワーク最適化**: HTTP接続プーリング
4. **ローカルLLM対応**: Ollama統合強化

## 依存関係

### 主要ライブラリ

```toml
[project.dependencies]
chardet = ">=5.2.0"
edinet-xbrl = ">=0.2.0"
langchain = ">=0.3.26"
langchain-community = ">=0.3.27"
langchain-openai = ">=0.3.27"
langgraph = ">=0.5.2"
pandas = ">=2.3.1"
requests = ">=2.32.4"
streamlit = ">=1.46.1"
```

### 開発用ライブラリ

```toml
[dependency-groups.dev]
psutil = ">=7.0.0"
pytest-mock = ">=3.14.1"
requests-mock = ">=1.12.1"
```

## まとめ

ステップ4までの実装により、自然言語での財務データ質問応答が可能なAIエージェントが完成しました。LangGraphによる柔軟なワークフロー制御、包括的なエラーハンドリング、メモリ機能による会話継続など、プロダクション品質の機能を備えています。

次のステップ5では、このエージェントを活用したユーザーフレンドリーなWebインターフェースを実装し、システム全体を完成させる予定です。