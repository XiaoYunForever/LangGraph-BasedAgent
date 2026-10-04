from typing import Any

from langgraph.types import Command, interrupt


def make_result_human_check(
    *,
    agent: str,
    human_node: str,
    afterprocess_node: str,
):
    def human_check(state: dict[str, Any]):

        decision = interrupt({
            "type": "subagent_result_approval",
            "agent": agent,
            "work_id": state["work_id"],
            "instruction": state["query"],
            "result": state["final_result"],
            "options": ["approve", "edit"],
        })

        # 1. 人工批准
        if isinstance(decision, dict):
            if decision.get("action") == "approve":
                return Command(
                    goto=afterprocess_node
                )

            # 2. 人工修改结果
            if decision.get("action") == "edit":

                new_result = decision.get("result")

                if (
                    isinstance(new_result, str)
                    and new_result.strip()
                ):
                    return Command(
                        update={
                            "final_result": new_result
                        },
                        goto=afterprocess_node
                    )

        # 3. 回复格式不合法：
        # 再次发起人工审批
        return Command(
            goto=human_node
        )

    return human_check