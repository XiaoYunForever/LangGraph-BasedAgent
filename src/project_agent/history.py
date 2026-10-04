from pprint import pprint

from langgraph.graph.state import CompiledStateGraph


def get_latest_state(graph:CompiledStateGraph,config:dict[str, dict[str, str]]):
    snapshot = graph.get_state(config)
    return snapshot

# def get_history(graph:CompiledStateGraph,config:dict[str, dict[str, str]]):
#     history = [graph.get_state_history(config)]
#     return history
def get_history(
    graph,
    config
):
    return list(
        graph.get_state_history(
            config
        )
    )

def find_checkpoint(
    graph,
    config,
    predicate,
):

    for snapshot in graph.get_state_history(
        config
    ):
        if predicate(snapshot):
            return snapshot

    return None

def inspect_checkpoint(
    checkpointer,
    config,
):
    checkpoint_tuple = (
        checkpointer.get_tuple(config)
    )

    if checkpoint_tuple is None:
        print("checkpoint not found")
        return

    print("\n=== CONFIG ===")
    pprint(checkpoint_tuple.config)

    print("\n=== CHECKPOINT ===")
    pprint(checkpoint_tuple.checkpoint)

    print("\n=== METADATA ===")
    pprint(checkpoint_tuple.metadata)

    print("\n=== PARENT CONFIG ===")
    pprint(checkpoint_tuple.parent_config)

    print("\n=== PENDING WRITES ===")
    pprint(checkpoint_tuple.pending_writes)





def inspect_versions(
    checkpointer,
    config,
):
    cp_tuple = checkpointer.get_tuple(
        config
    )

    if cp_tuple is None:
        print("checkpoint not found")
        return

    cp = cp_tuple.checkpoint

    print("\n" + "=" * 60)
    print("UPDATED CHANNELS")
    print("=" * 60)

    pprint(
        cp.get(
            "updated_channels"
        )
    )

    print("\n" + "=" * 60)
    print("CHANNEL VERSIONS")
    print("=" * 60)

    for channel, version in (
        cp["channel_versions"].items()
    ):
        print(
            f"{channel:<40} "
            f"{version}"
        )

    print("\n" + "=" * 60)
    print("VERSIONS SEEN")
    print("=" * 60)

    for node, seen in (
        cp["versions_seen"].items()
    ):
        print(
            f"\nNODE: {node}"
        )

        for channel, version in (
            seen.items()
        ):
            print(
                f"  {channel:<38} "
                f"{version}"
            )

def inspect_nested_interrupts(graph, config):

    root_snapshot = graph.get_state(
        config,
        subgraphs=True
    )

    interrupt_map = {}

    def walk(snapshot, depth=0):

        prefix = "  " * depth

        namespace = snapshot.config.get(
            "configurable", {}
        ).get("checkpoint_ns", "")

        print(
            prefix,
            "NAMESPACE:",
            namespace
        )

        print(
            prefix,
            "NEXT:",
            snapshot.next
        )

        for task in snapshot.tasks:

            print(
                prefix,
                "TASK:",
                task.name,
                task.id
            )

            # 记录 Interrupt
            for item in task.interrupts:

                payload = item.value

                if (
                    isinstance(payload, dict)
                    and payload.get("type")
                    == "subagent_result_approval"
                ):
                    interrupt_map[item.id] = payload

                    print(
                        prefix,
                        "INTERRUPT:",
                        item.id,
                        payload["agent"],
                        payload["work_id"]
                    )

            # 递归进入 Structural Subgraph
            child_state = getattr(
                task, "state", None
            )

            if hasattr(child_state, "tasks"):
                walk(child_state, depth + 1)

    walk(root_snapshot)

    return interrupt_map