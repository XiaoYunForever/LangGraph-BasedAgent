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
    # config = {
    #     "configurable": {
    #
    #         "thread_id":
    #             "demo"
    #     }
    # }
    #
    #
    # initial_state = {
    #     "帮我简短介绍并写一个Python冒泡排序"
    # }
    #
    # for chunk in parent_graph.stream(
    #
    #     initial_state,
    #
    #     config=config,
    #
    #     stream_mode=[
    #         "updates"
    #     ]
    # ):
    #     print("\n" + "=" * 60)
    #     print(chunk)
    #     print("\n" + "=" * 60)