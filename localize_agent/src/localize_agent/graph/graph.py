"""Build and compile the localization LangGraph workflow."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from localize_agent.graph.nodes import (
    evidence_collector_node,
    issue_localizer_node,
    ranker_node,
)
from localize_agent.graph.state import AnalysisState


def build_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("evidence_collector", evidence_collector_node)
    graph.add_node("issue_localizer", issue_localizer_node)
    graph.add_node("ranker", ranker_node)

    graph.add_edge(START, "evidence_collector")
    graph.add_edge("evidence_collector", "issue_localizer")
    graph.add_edge("issue_localizer", "ranker")
    graph.add_edge("ranker", END)

    return graph.compile()
