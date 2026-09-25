from langgraph.types import Send
from langgraph.runtime import Runtime
from langgraph.types import Command

from .state import *
from .model import *


def planner(state:OverallState):
    planner_model = model.with_structured_output(PlannerOutput)
    input = f"""
        根据用户需求{state["goal"]}
        拆分细化任务为不同的task给子agent，每个子任务只做一件事。，一种任务可以由子agent并行完成
        目前可用子agent有：
        research：查找任务涉及的相关资料
        coder：根据用户的需求完成代码
        writer：完成对用户需求的回答。如果有资料或者代码则进行参考
        
        work_id 必须唯一
        depends_on 只能引用存在的 work_id
        禁止任务依赖自身
        禁止循环依赖
        """
    plan = planner_model.invoke(input)

    return {
        "tasks": plan.tasks
    }

def Scheduler(state:OverallState):
    all_finished_tasks = {
        task["work_id"]
        for task in state["task_results"]
    }

    remaining_tasks = [
        task
        for task in state["tasks"]
        if task.work_id
           not in all_finished_tasks
    ]

    if not remaining_tasks:
        return Command(
            goto="aggregate"
        )

    ready_tasks = [
        task
        for task in remaining_tasks
        if set(
            task.depends_on
        ).issubset(
            all_finished_tasks
        )
    ]

    if not ready_tasks:
        return Command(
            update={
                "error":
                    "Dependency deadlock: "
                    "cycle or missing work_id"
            },
            goto="dependency_error"
        )

    sends = []

    for task in ready_tasks:
        dependency_results = {
            result["work_id"]:
                result["result"]

            for result
            in state["task_results"]

            if result["work_id"]
               in task.depends_on
        }

        sends.append(
            Send(
                "worker",
                {
                    "work_id":
                        task.work_id,

                    "agent":
                        task.agent,

                    "instruction":
                        task.instruction,

                    "dependency_results":
                        dependency_results,
                }
            )
        )

    next_wave = (
            state.get("wave", 0)
            + 1
    )

    return Command(
        update={
            "wave":
                next_wave
        },
        goto=sends
    )

def worker(state:WorkerState):
    if state["agent"] == "research":

        result = researcher({
            "query":
                state["instruction"],

            "dependency_results":
                state["dependency_results"],

            "research_result":
                "",
        })

    elif state["agent"] == "coder":

        result = coder({
            "query":
                state["instruction"],

            "dependency_results":
                state["dependency_results"],

            "code_result":
                "",
        })

    elif state["agent"] == "writer":

        result = writer({
            "query":
                state["instruction"],

            "dependency_results":
                state["dependency_results"],

            "write_result":
                "",
        })

    else:
        raise ValueError(
            f"Unknown agent: {state['agent']}"
        )

    return {
        "task_results": [
            {
                "work_id":
                    state["work_id"],

                "result":
                    result,
            }
        ]
    }

def dependency_error(state:OverallState):
    return {
        "final_answer":state["error"]
    }

def aggregate(state:OverallState):

    ordered = sorted(
        state["task_results"],
        key=lambda x: x["work_id"]
    )

    final = "\n\n".join(
        f'{r["work_id"]}: {r["result"]}'
        for r in ordered
    )

    return {
        "final_answer":
            final
    }

# Researcher==========================================================
def researcher(state:ResearchState):
    researcher_model = model.with_structured_output(ResearchOutput)
    input = f"""
        根据用户需求：{state["query"]}
        完成research工作。
        参考资料如下：
        {state["dependency_results"]}
    """
    response = researcher_model.invoke(input)
    return {"research_result":response.result}
# Coder===============================================================
def coder(state:CodingState):
    coding_model = model.with_structured_output(CodingOutput)
    input = f"""
            根据用户需求：{state["query"]}
            完成coding工作。
            参考资料如下：
            {state["dependency_results"]}
        """
    response = coding_model.invoke(input)

    return {"code_result":response.result}
# Writer==============================================================
def writer(state:WriteState):
    writing_model = model.with_structured_output(WriterOutput)
    input = f"""
            根据用户需求：{state["query"]}
            完成write工作。
            参考资料如下：
            {state["dependency_results"]}
        """
    response = writing_model.invoke(input)

    return {"write_result":response.result}
