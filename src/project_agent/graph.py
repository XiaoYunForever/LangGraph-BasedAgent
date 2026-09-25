from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .nodes import *


def build_graph():
    parent_builder = StateGraph(OverallState)

    parent_builder.add_node("planner",planner)
    parent_builder.add_node("worker",worker)
    parent_builder.add_node("Scheduler",Scheduler)
    parent_builder.add_node("aggregate",aggregate)
    parent_builder.add_node("dependency_error",dependency_error)

    parent_builder.add_edge(START,"planner")
    parent_builder.add_edge("planner","Scheduler")
    parent_builder.add_edge("worker","Scheduler")
    parent_builder.add_edge("aggregate",END)
    parent_builder.add_edge("dependency_error",END)

    parent_graph = parent_builder.compile(checkpointer=InMemorySaver())
    return parent_graph

def build_research_graph():
    research_builder = StateGraph(ResearchState)

    research_builder.add_node("researcher",researcher)
    research_builder.add_node("research_reviewer",research_reviewer)

    research_builder.add_edge(START,"researcher")
    research_builder.add_edge("researcher","research_reviewer")
    research_builder.add_edge("research_reviewer",END)

    research_graph = research_builder.compile()
    return research_graph


def build_code_graph():
    code_builder = StateGraph(CodingState)

    code_builder.add_node("coder", coder)
    code_builder.add_node("coding_reviewer", coding_reviewer)

    code_builder.add_edge(START, "coder")
    code_builder.add_edge("coder","coding_reviewer")
    code_builder.add_edge("coding_reviewer", END)

    code_graph = code_builder.compile()
    return code_graph


def build_write_graph():
    write_builder = StateGraph(WriteState)

    write_builder.add_node("writer", writer)
    write_builder.add_node("write_reviewer", write_reviewer)

    write_builder.add_edge(START, "writer")
    write_builder.add_edge("writer","write_reviewer")
    write_builder.add_edge("write_reviewer", END)

    write_graph = write_builder.compile()
    return write_graph