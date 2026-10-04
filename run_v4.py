from pathlib import Path
from pprint import pprint

from langgraph.checkpoint.sqlite import SqliteSaver
from project_agent import build_graph


DB_PATH = Path(__file__).resolve().parent / "checkpoints.sqlite"

config = {
    "configurable": {
        "thread_id": "hitl-demo-001"
    }
}

initial_state = {
    "goal": "帮我简短介绍并写一个Python冒泡排序",
    "tasks": [],
    "task_results": [],
    "wave": 0,
    "final_answer": "",
    "error": "",
    "approval_status": "pending",
    "plan_origin": "planner",
    "validation_errors": [],
}


with SqliteSaver.from_conn_string(
    str(DB_PATH)
) as checkpointer:

    graph = build_graph(checkpointer)

    print("\n=== FIRST EXECUTION ===")

    for chunk in graph.stream(
        initial_state,
        config=config,
        stream_mode="updates",
    ):
        pprint(chunk)

    snapshot = graph.get_state(config)

    print("\n=== PAUSED STATE ===")
    print("next =", snapshot.next)
    print("approval_status =", snapshot.values.get("approval_status"))

    for task in snapshot.tasks:
        print("task =", task.name)
        print("interrupts =", task.interrupts)