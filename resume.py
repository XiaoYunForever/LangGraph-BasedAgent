from langgraph.checkpoint.sqlite import SqliteSaver

from project_agent import build_graph
from project_agent.history import get_history, find_checkpoint, inspect_checkpoint, inspect_versions, \
    inspect_trigger_values


def main():

    config = {
        "configurable": {
            "thread_id": "demo-001"
        }
    }

    with SqliteSaver.from_conn_string(
        "checkpoints.sqlite"
    ) as checkpointer:

        graph = build_graph(
            checkpointer
        )

        history = get_history(
            graph,
            config
        )

        print(
            "\nRESTORED HISTORY"
        )

        for i, snapshot in enumerate(
            history,
            start=1
        ):

            checkpoint_id = (
                snapshot.config
                ["configurable"]
                ["checkpoint_id"]
            )

            print(
                f"#{i}",
                f"checkpoint_id={checkpoint_id}",
                f"next={snapshot.next}"
            )
        # 1
        checkpoint1 = find_checkpoint(
            graph,
            config,
            lambda snapshot:
            snapshot.next == ("writer",)
        )

        if checkpoint1 is None:
            print("没有找到目标 checkpoint1")
            return

        inspect_versions(
            checkpointer,
            checkpoint1.config
        )
        # 2
        print("\n")
        checkpoint2 = find_checkpoint(
            graph,
            config,
            lambda snapshot:
            snapshot.next == ("Scheduler",)
        )

        if checkpoint2 is None:
            print("没有找到目标 checkpoint2")
            return

        inspect_versions(
            checkpointer,
            checkpoint2.config
        )
        print("\n")
        # 3
        checkpoint3 = find_checkpoint(
            graph,
            config,
            lambda snapshot:
            snapshot.next == ("aggregate",)
        )

        if checkpoint3 is None:
            print("没有找到目标 checkpoint3")
            return

        inspect_versions(
            checkpointer,
            checkpoint3.config
        )
    print("\n")




















#         for chunk in graph.stream(
#                 None,
#                 config=checkpoint.config,
#                 stream_mode="updates",
#         ):
#             print(chunk)
# # ================================================================================
#         fork_config = graph.update_state(
#             checkpoint.config,
#             {
#                 "wave": 99
#             }
#         )
#         fork = graph.invoke(
#             None,
#             config=fork_config
#         )
#         print("\n")
#         print("FORK:")
#         print(fork)

if __name__ == "__main__":
    main()