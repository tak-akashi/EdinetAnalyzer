"""
EDINET分析システム

日本の金融庁が提供するEDINETシステムからXBRLデータを取得し、
LangGraphを使用してAIエージェントによる自然言語での財務分析を行うシステム
"""

from .agent import EdinetAnalysisAgent, create_agent
from .state import EdinetAgentState, create_initial_state
from .nodes import EdinetAgentNodes
from .edges import router, should_continue

__version__ = "0.1.0"

__all__ = [
    "EdinetAnalysisAgent",
    "create_agent",
    "EdinetAgentState", 
    "create_initial_state",
    "EdinetAgentNodes",
    "router",
    "should_continue"
]