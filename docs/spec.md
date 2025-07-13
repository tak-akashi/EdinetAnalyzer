# 自然言語によるEDINET検索アプリケーション

## 目標（Goal）
 - 日本の上場企業の開示資料についての質問を投げるとEdinetを検索して、当該質問に回答するWebアプリケーションを作る

## 技術スタック（Tech）
- Python, Streamlit, LangGraph, LangChain, ollama
- LLM: GPT-4o等のプロプライアトリーモデルやオープンソースモデルから選択

## 参考
### EDINETについて
- EDINET（Electronic Disclosure for Investors' NETwork）は、金融庁が運営する、日本のすべての上場企業による法定開示書類の電子的提出・閲覧システムである。これは、有価証券報告書や財務諸表に関する「信頼できる唯一の情報源」である。
- EDINET API（現行バージョンはv2）は、これらの開示書類をプログラムで検索し、取得することを可能にする 7。ユーザーは日付範囲などを指定して書類リストを照会し、特定の書類をそのdocID（書類管理番号）によってダウンロードできる 34。APIの利用には、EDINETのAPIポータルサイトでのユーザー登録と、電話番号認証を含むAPIキーの取得が必要となる。
- ここでの主要な技術的課題は、XBRL（eXtensible Business Reporting Language）の扱いに集約される。開示書類に含まれる中核的な財務データは、このXBRL形式で構造化されている 32。XBRLは、財務諸表を機械可読にするための世界標準のフォーマットであるが、そのXMLベースの構造は複雑である。Pythonでこのデータを解析するためには、edinet-xbrl 39 のような専用ライブラリや、その他のXBRLパーサーを利用する必要がある。
- 典型的なワークフローは以下のようになる。
  (1) EDINET APIで書類リストを取得
  (2) 特定の開示書類のZIPファイルをダウンロード
  (3) ZIPファイルからXBRLファイルを展開
  (4) パーサーライブラリを用いてXBRLを読み込み、「資産」や「売上高」といった目的の財務データを抽出し、pandas DataFrameのような構造化データに変換する 

### EDINET API（現行バージョンはv2）の仕様等の資料
  - https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html