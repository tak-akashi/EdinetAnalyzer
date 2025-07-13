"""
EDINET分析システム - Streamlit Web UI

このモジュールは、EDINET分析エージェントを使用したWebインターフェースを提供します。
ユーザーは自然言語で財務データに関する質問を入力し、
AIエージェントが自動的にEDINETから情報を取得・分析して回答を生成します。
"""

import os
import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit page config
st.set_page_config(
    page_title="EDINET財務分析システム",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """セッション状態の初期化"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"
    if "api_key_edinet" not in st.session_state:
        st.session_state.api_key_edinet = os.getenv("EDINET_API_KEY", "")
    if "api_key_openai" not in st.session_state:
        st.session_state.api_key_openai = os.getenv("OPENAI_API_KEY", "")
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gpt-4o"
    if "enable_memory" not in st.session_state:
        st.session_state.enable_memory = True

def setup_sidebar():
    """サイドバーの設定"""
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # API設定
        st.subheader("API設定")
        
        edinet_key = st.text_input(
            "EDINET APIキー",
            value=st.session_state.api_key_edinet,
            type="password",
            help="EDINET APIキーを入力してください"
        )
        
        openai_key = st.text_input(
            "OpenAI APIキー", 
            value=st.session_state.api_key_openai,
            type="password",
            help="OpenAI APIキーを入力してください"
        )
        
        # モデル設定
        st.subheader("モデル設定")
        model_name = st.selectbox(
            "使用モデル",
            ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            index=0,
            help="使用するLLMモデルを選択してください"
        )
        
        enable_memory = st.checkbox(
            "メモリ機能を有効化",
            value=st.session_state.enable_memory,
            help="会話履歴を保持して継続的な対話を可能にします"
        )
        
        # 設定保存
        if st.button("設定を保存"):
            st.session_state.api_key_edinet = edinet_key
            st.session_state.api_key_openai = openai_key
            st.session_state.model_name = model_name
            st.session_state.enable_memory = enable_memory
            st.session_state.agent = None  # エージェントを再初期化
            st.success("設定を保存しました")
        
        # システム情報
        st.subheader("システム情報")
        st.info(f"セッションID: {st.session_state.session_id}")
        st.info(f"会話数: {len(st.session_state.messages)}")
        
        # 会話履歴クリア
        if st.button("会話履歴をクリア"):
            st.session_state.messages = []
            st.session_state.agent = None
            st.success("会話履歴をクリアしました")

def get_agent():
    """エージェントの取得または初期化"""
    if st.session_state.agent is None:
        try:
            import sys
            import os
            # プロジェクトルートをパスに追加
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from src.edinet_analyzer import create_agent
            
            # 環境変数を一時的に設定
            if st.session_state.api_key_edinet:
                os.environ["EDINET_API_KEY"] = st.session_state.api_key_edinet
            if st.session_state.api_key_openai:
                os.environ["OPENAI_API_KEY"] = st.session_state.api_key_openai
            
            # エージェント作成
            st.session_state.agent = create_agent(
                model_name=st.session_state.model_name,
                enable_memory=st.session_state.enable_memory
            )
            
            logger.info(f"エージェントを初期化しました (model: {st.session_state.model_name})")
            
        except Exception as e:
            logger.error(f"エージェント初期化エラー: {e}")
            st.error(f"エージェントの初期化に失敗しました: {str(e)}")
            return None
    
    return st.session_state.agent

def validate_configuration():
    """設定の検証"""
    issues = []
    
    if not st.session_state.api_key_edinet:
        issues.append("EDINET APIキーが設定されていません")
    
    if not st.session_state.api_key_openai:
        issues.append("OpenAI APIキーが設定されていません")
    
    return issues

def main():
    """メインアプリケーション"""
    # セッション状態初期化
    initialize_session_state()
    
    # ヘッダー
    st.title("📊 EDINET財務分析システム")
    st.markdown("""
    このシステムは、EDINETから企業の財務データを自動取得し、
    AIエージェントが自然言語で分析結果を提供します。
    """)
    
    # サイドバー設定
    setup_sidebar()
    
    # 設定検証
    config_issues = validate_configuration()
    if config_issues:
        st.warning("⚠️ 設定に不備があります:")
        for issue in config_issues:
            st.write(f"• {issue}")
        st.info("左側のサイドバーから設定を行ってください。")
        return
    
    # エージェント取得
    agent = get_agent()
    if agent is None:
        st.error("エージェントの初期化に失敗しました。設定を確認してください。")
        return
    
    # 環境検証表示
    with st.expander("🔍 環境検証", expanded=False):
        try:
            validation = agent.validate_environment()
            for check, status in validation.items():
                icon = "✅" if status else "❌"
                st.write(f"{icon} {check}: {'OK' if status else 'NG'}")
        except Exception as e:
            st.error(f"環境検証エラー: {e}")
    
    # メインコンテンツエリア
    st.header("💬 質問入力")
    
    # 質問例を表示
    with st.expander("💡 質問例", expanded=False):
        examples = [
            "楽天グループの最新の総資産を教えてください",
            "ソフトバンクグループの純利益を調べて",
            "トヨタ自動車の財務状況を分析してください",
            "三菱UFJフィナンシャル・グループの自己資本比率は？",
            "任天堂の売上高と営業利益を比較してください"
        ]
        for example in examples:
            if st.button(f"📝 {example}", key=f"example_{hash(example)}"):
                st.session_state.query_input = example
    
    # 質問入力フォーム
    query = st.text_area(
        "財務データについて質問してください:",
        height=100,
        placeholder="例: 楽天グループの最新の総資産を教えてください",
        key="query_input"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        submit_button = st.button("🔍 分析実行", type="primary")
    
    with col2:
        if st.button("🗑️ 結果クリア"):
            st.session_state.messages = []
            st.rerun()
    
    # 分析実行
    if submit_button and query.strip():
        # メッセージ追加
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": query,
            "timestamp": timestamp
        })
        
        # 処理状況表示
        with st.spinner("🤖 AIエージェントが分析を実行中..."):
            try:
                # 設定準備
                config = None
                if st.session_state.enable_memory:
                    config = {"configurable": {"thread_id": st.session_state.session_id}}
                
                # エージェント実行
                start_time = time.time()
                result = agent.invoke(query, config=config)
                execution_time = time.time() - start_time
                
                # 結果をメッセージに追加
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("final_answer", "回答を生成できませんでした"),
                    "timestamp": timestamp,
                    "execution_time": execution_time,
                    "metadata": {
                        "search_results": result.get("search_results"),
                        "downloaded_files": result.get("downloaded_files"),
                        "xbrl_analysis": result.get("xbrl_analysis"),
                        "tool_calls": result.get("tool_calls", [])
                    }
                })
                
                st.rerun()
                
            except Exception as e:
                logger.error(f"分析実行エラー: {e}")
                st.session_state.messages.append({
                    "role": "error",
                    "content": f"エラーが発生しました: {str(e)}",
                    "timestamp": timestamp
                })
                st.rerun()
    
    # 会話履歴表示
    if st.session_state.messages:
        st.header("💭 分析結果")
        
        for i, message in enumerate(reversed(st.session_state.messages)):
            if message["role"] == "user":
                with st.container():
                    st.markdown(f"**🧑 ユーザー** ({message['timestamp']})")
                    st.markdown(f"> {message['content']}")
                    
            elif message["role"] == "assistant":
                with st.container():
                    st.markdown(f"**🤖 AIエージェント** ({message['timestamp']})")
                    st.markdown(message['content'])
                    
                    # 実行時間表示
                    if "execution_time" in message:
                        st.caption(f"⏱️ 実行時間: {message['execution_time']:.2f}秒")
                    
                    # メタデータ表示
                    if "metadata" in message and message["metadata"]:
                        with st.expander("📋 詳細情報", expanded=False):
                            metadata = message["metadata"]
                            
                            if metadata.get("search_results"):
                                st.subheader("🔍 検索結果")
                                for j, doc in enumerate(metadata["search_results"][:3]):
                                    st.write(f"**書類{j+1}**: {doc.get('filerName', 'N/A')} - {doc.get('docDescription', 'N/A')}")
                            
                            if metadata.get("downloaded_files"):
                                st.subheader("📁 ダウンロードファイル")
                                for file_path in metadata["downloaded_files"]:
                                    st.write(f"• {file_path}")
                            
                            if metadata.get("tool_calls"):
                                st.subheader("🛠️ 実行されたツール")
                                for call in metadata["tool_calls"][-3:]:
                                    st.write(f"• {call.get('tool_name', 'Unknown')}")
                                    
            elif message["role"] == "error":
                with st.container():
                    st.error(f"**❌ エラー** ({message['timestamp']})")
                    st.error(message['content'])
            
            if i < len(st.session_state.messages) - 1:
                st.divider()

if __name__ == "__main__":
    main()