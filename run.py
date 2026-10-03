from langgraph.checkpoint.sqlite import SqliteSaver

from project_agent import build_graph
from project_agent.history import get_history


def main():

    config = {
        "configurable": {
            "thread_id": "demo-001"
        }
    }

    initial_state = {
        "goal": "帮我简短介绍并写一个Python冒泡排序",
        "tasks": [],
        "task_results": [],
        "wave": 0,
        "final_answer": "",
        "error": "",
    }

    with SqliteSaver.from_conn_string(
        "checkpoints.sqlite"
    ) as checkpointer:

        graph = build_graph(
            checkpointer
        )

        for chunk in graph.stream(
            initial_state,
            config=config,
            stream_mode="tasks",
        ):
            print(chunk)

        print("\nCHECKPOINT HISTORY")

        history = get_history(
            graph,
            config
        )

        for snapshot in history:

            print(
                snapshot.config[
                    "configurable"
                ][
                    "checkpoint_id"
                ],
                snapshot.next
            )


if __name__ == "__main__":
    main()