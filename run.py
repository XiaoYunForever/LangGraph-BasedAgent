from pprint import pprint
from project_agent import build_graph

def main():
    graph = build_graph()
    config = {"configurable": {"thread_id": "demo"}}
    initial_state = {
        "goal": "帮我简短介绍并写一个Python冒泡排序",
        "tasks": [],
        "task_results": [],
        "wave": 0,
        "final_answer": "",
        "error": "",
    }

    print("=" * 60)
    print("STREAM UPDATES")
    print("=" * 60)
    for chunk in graph.stream(
        initial_state,
        config=config,
        stream_mode="updates",
    ):
        pprint(chunk)

    snapshot = graph.get_state(config)
    print("\nLATEST STATE")
    pprint(snapshot.values)
    print("next =", snapshot.next)
    print("tasks =", snapshot.tasks)

    print("\nCHECKPOINT HISTORY (newest first)")
    for i, item in enumerate(graph.get_state_history(config), start=1):
        checkpoint_id = item.config.get("configurable", {}).get("checkpoint_id")
        completed = [
            x["work_id"]
            for x in item.values.get("task_results", [])
        ]
        print(
            f"#{i} checkpoint_id={checkpoint_id} "
            f"next={item.next} wave={item.values.get('wave')} "
            f"completed={completed}"
        )

if __name__ == "__main__":
    main()
