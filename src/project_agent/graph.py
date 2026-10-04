from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from project_agent.human_check import make_result_human_check

from .nodes import *


def build_graph(checkpointer):
    parent_builder = StateGraph(OverallState)

    parent_builder.add_node("planner",planner)
    parent_builder.add_node("plan_validator",plan_validator)
    parent_builder.add_node("human_review",human_review)
    parent_builder.add_node("Scheduler",Scheduler)
    parent_builder.add_node("aggregate",aggregate)
    parent_builder.add_node("dependency_error",dependency_error)

    parent_builder.add_node("researcher",build_research_graph())
    parent_builder.add_node("coder", build_code_graph())
    parent_builder.add_node("writer", build_write_graph())

    parent_builder.add_edge(START,"planner")
    parent_builder.add_edge("planner","plan_validator")
    parent_builder.add_edge("researcher","Scheduler")
    parent_builder.add_edge("coder", "Scheduler")
    parent_builder.add_edge("writer", "Scheduler")
    parent_builder.add_edge("aggregate",END)
    parent_builder.add_edge("dependency_error",END)

    parent_graph = parent_builder.compile(checkpointer=checkpointer)
    return parent_graph

def build_research_graph():
    research_builder = StateGraph(ResearchState,
                                  input_schema=SubAgentInput,
                                  output_schema=SubAgentOutput)

    research_builder.add_node("researcher",researcher)
    research_builder.add_node("research_reviewer",research_reviewer)
    research_builder.add_node("research_afterprocess", research_afterprocess)
    research_builder.add_node(
        "research_human_check",
        make_result_human_check(
            agent="research",
            human_node="research_human_check",
            afterprocess_node="research_afterprocess",
        )
    )

    research_builder.add_edge(START,"researcher")
    research_builder.add_edge("researcher","research_reviewer")
    research_builder.add_edge("research_afterprocess",END)

    research_graph = research_builder.compile()
    return research_graph


def build_code_graph():
    code_builder = StateGraph(CodingState,
                              input_schema=SubAgentInput,
                              output_schema=SubAgentOutput
                              )

    code_builder.add_node("coder", coder)
    code_builder.add_node("coding_reviewer", coding_reviewer)
    code_builder.add_node("code_afterprocess", code_afterprocess)
    code_builder.add_node(
        "coding_human_check",
        make_result_human_check(
            agent="coder",
            human_node="coding_human_check",
            afterprocess_node="code_afterprocess",
        )
    )

    code_builder.add_edge(START, "coder")
    code_builder.add_edge("coder","coding_reviewer")
    code_builder.add_edge("code_afterprocess", END)

    code_graph = code_builder.compile()
    return code_graph


def build_write_graph():
    write_builder = StateGraph(WriteState,
                               input_schema=SubAgentInput,
                               output_schema=SubAgentOutput
                               )

    write_builder.add_node("writer", writer)
    write_builder.add_node("write_reviewer", write_reviewer)
    write_builder.add_node("write_afterprocess", write_afterprocess)

    write_builder.add_edge(START, "writer")
    write_builder.add_edge("writer","write_reviewer")
    write_builder.add_edge("write_afterprocess", END)

    write_graph = write_builder.compile()
    return write_graph