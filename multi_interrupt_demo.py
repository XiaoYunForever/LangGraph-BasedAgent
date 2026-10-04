import sys
from pathlib import Path
from typing_extensions import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.checkpoint.sqlite import SqliteSaver


DB_PATH = Path(__file__).resolve().parent / "multi_hitl.sqlite"

CONFIG = {
    "configurable": {
        "thread_id": "multi-interrupt-001"
    }
}


# ====================================================
# State
# ====================================================

class ApprovalState(TypedDict):
    goal: str
    research_decision: NotRequired[str]
    coding_decision: NotRequired[str]
    final_status: NotRequired[str]


# ====================================================
# Research Review
# ====================================================

def research_review(state: ApprovalState):

    print(">>> ENTER RESEARCH REVIEW")

    decision = interrupt({
        "agent": "research",
        "question": "是否批准 Research 任务？",
        "goal": state["goal"]
    })

    print("RESEARCH RESUMED:", decision)

    return {
        "research_decision": decision["action"]
    }


# ====================================================
# Coding Review
# ====================================================

def coding_review(state: ApprovalState):

    print(">>> ENTER CODING REVIEW")

    decision = interrupt({
        "agent": "coder",
        "question": "是否批准 Coding 任务？",
        "goal": state["goal"]
    })

    print("CODING RESUMED:", decision)

    return {
        "coding_decision": decision["action"]
    }


# ====================================================
# Aggregate
# ====================================================

def aggregate(state: ApprovalState):

    research_ok = (
        state["research_decision"] == "approve"
    )

    coding_ok = (
        state["coding_decision"] == "approve"
    )

    return {
        "final_status": (
            "approved"
            if research_ok and coding_ok
            else "blocked"
        )
    }


# ====================================================
# Graph
# ====================================================

def build_graph(checkpointer):

    builder = StateGraph(ApprovalState)

    builder.add_node("research_review", research_review)
    builder.add_node("coding_review", coding_review)
    builder.add_node("aggregate", aggregate)

    # 并行 Fan-out
    builder.add_edge(START, "research_review")
    builder.add_edge(START, "coding_review")

    # 等待两个 Review Node 都完成
    builder.add_edge(
        ["research_review", "coding_review"],
        "aggregate"
    )

    builder.add_edge("aggregate", END)

    return builder.compile(
        checkpointer=checkpointer
    )


# ====================================================
# 查看待处理 Interrupt
# ====================================================

def show_interrupts(graph):

    snapshot = graph.get_state(CONFIG)

    print("\n=== CHECKPOINT ===")
    print("next =", snapshot.next)

    print("\n=== TASKS ===")

    for task in snapshot.tasks:
        print("task_name =", task.name)
        print("task_id =", task.id)

        for item in task.interrupts:
            print("interrupt_id =", item.id)
            print("payload =", item.value)

    return snapshot


# ====================================================
# 第一次运行：暂停
# ====================================================

def start(graph):

    print("\n=== START ===")

    for chunk in graph.stream(
        {
            "goal": "研究并实现 Python 冒泡排序"
        },
        config=CONFIG,
        stream_mode="updates"
    ):
        print(chunk)

    show_interrupts(graph)


# ====================================================
# 第二次运行：精确恢复
# ====================================================

def resume(graph):

    snapshot = show_interrupts(graph)

    resume_map = {}

    for task in snapshot.tasks:

        for item in task.interrupts:

            agent = item.value["agent"]

            if agent == "research":
                resume_map[item.id] = {
                    "action": "approve"
                }

            elif agent == "coder":
                resume_map[item.id] = {
                    "action": "reject"
                }

    if len(resume_map) != 2:
        raise RuntimeError(
            "预期存在两个待恢复的 Interrupt"
        )

    print("\n=== RESUME MAP ===")
    print(resume_map)

    print("\n=== RESUME EXECUTION ===")

    for chunk in graph.stream(
        Command(resume=resume_map),
        config=CONFIG,
        stream_mode="updates"
    ):
        print(chunk)

    latest = graph.get_state(CONFIG)

    print("\n=== FINAL STATE ===")
    print(latest.values)
    print("next =", latest.next)


# ====================================================
# Main
# ====================================================


with SqliteSaver.from_conn_string(
    str(DB_PATH)
) as checkpointer:

    graph = build_graph(checkpointer)


    # start(graph)

    resume(graph)