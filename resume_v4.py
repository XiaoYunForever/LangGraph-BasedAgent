from pathlib import Path
from pprint import pprint

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from project_agent import build_graph
from project_agent.history import inspect_nested_interrupts

DB_PATH = Path(__file__).resolve().parent / "checkpoints.sqlite"

config = {
    "configurable": {
        "thread_id": "hitl-demo-001"
    }
}


with SqliteSaver.from_conn_string(
    str(DB_PATH)
) as checkpointer:

    graph = build_graph(checkpointer)

    # 先读取上次进程保存的暂停状态
    snapshot = graph.get_state(config)

    print("\n=== RESTORED STATE ===")
    print("next =", snapshot.next)

    pending_interrupts = [
        item
        for task in snapshot.tasks
        for item in task.interrupts
    ]

    if not pending_interrupts:
        raise RuntimeError("当前线程没有等待恢复的 interrupt")

    for item in pending_interrupts:
        print("interrupt_id =", item.id)
        # pprint(item.value)
    print("================================================")
    interrupts = inspect_nested_interrupts(
        graph,
        config
    )
    agents = {
        payload["agent"]
        for payload in interrupts.values()
    }

    if not {"research", "coder"}.issubset(agents):
        raise RuntimeError(
            "没有找到预期的两个子图审批中断"
        )
    # 为不同中断构建人工回复
    resume_map = {}

    for interrupt_id, payload in interrupts.items():

        if payload["agent"] == "research":
            resume_map[interrupt_id] = {
                "action": "approve"
            }

        elif payload["agent"] == "coder":
            resume_map[interrupt_id] = {
                "action": "approve"
            }

    print("\n=== RESUME MAP ===")
    pprint(resume_map)

    print("\n=== RESUME ===")

    for chunk in graph.stream(
            Command(resume=resume_map),
            config=config,
            stream_mode="updates",
            subgraphs=True
    ):
        pprint(chunk)

    latest = graph.get_state(config)

    print("\n=== FINAL ===")
    print("next =", latest.next)
    print(
        "completed =",
        [
            item["work_id"]
            for item in latest.values.get(
            "task_results", []
        )
        ]
    )

    # 以下为parentGraph的HITL的resume操作
    # edited_plan = [
    # {
    #     "work_id": "research_1",
    #     "agent": "research",
    #     "instruction": (
    #         "介绍冒泡排序的核心思想、"
    #         "时间复杂度、空间复杂度与稳定性。"
    #     ),
    #     "depends_on": [],
    # },
    # {
    #     "work_id": "code_1",
    #     "agent": "coder",
    #     "instruction": (
    #         "编写可运行的 Python 冒泡排序，"
    #         "包含提前终止优化和简单测试。"
    #     ),
    #     "depends_on": [],
    # },
    # {
    #     "work_id": "write_1",
    #     "agent": "writer",
    #     "instruction": (
    #         "整合研究介绍和代码，"
    #         "生成简洁完整的最终回答。"
    #     ),
    #     "depends_on": [
    #         "research_1",
    #         "code_1"
    #     ],
    # },
    # ]
    # # 人工同意执行计划
    # decision = {
    #     "action": "edit",
    #     "tasks": edited_plan
    # }
    # print("\n=== RESUME ===")
    # for chunk in graph.stream(
    #         Command(resume=decision),
    #         config=config,
    #         stream_mode="updates"
    # ):
    #     pprint(chunk)
    #
    #
    #
    # latest = graph.get_state(config)
    #
    # print("\n=== FINAL STATE ===")
    # print("next =", latest.next)
    # print(
    #     "approval_status =",
    #     latest.values.get("approval_status")
    # )
    #
    # print("\n=== FFFFFINAL STATE ===")
    # for chunk in graph.stream(
    #         Command(
    #             resume={"action": "approve"}
    #         ),
    #         config=config,
    #         stream_mode="updates"
    # ):
    #     pprint(chunk)