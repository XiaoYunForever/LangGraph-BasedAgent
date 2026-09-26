from langgraph.types import Send
from langgraph.runtime import Runtime
from langgraph.types import Command
from .state import *

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
        if task.agent == "research":
            sends.append(
                Send(
                    "researcher",
                    {
                        "work_id":
                            task.work_id,

                        "query":
                            task.instruction,

                        "dependency_results":
                            dependency_results,
                    }
                )
            )
        elif task.agent == "coder":
            sends.append(
                Send(
                    "coder",
                    {
                        "work_id":
                            task.work_id,

                        "query":
                            task.instruction,

                        "dependency_results":
                            dependency_results,
                    }
                )
            )
        else:
            sends.append(
                Send(
                    "writer",
                    {
                        "work_id":
                            task.work_id,

                        "query":
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
    from .graph import (
        build_research_graph,
        build_code_graph,
        build_write_graph,
    )
    if state["agent"] == "research":
        research_input = {
            "query":state["instruction"],
            "draft":"",
            "retry_count":0,
            "advice":"",
            "research_result":"",
            "dependency_results":state["dependency_results"]
        }
        research_graph = build_research_graph()
        result = research_graph.invoke(research_input)["research_result"]

        # specialist_result = researcher({
        #     "query":
        #         state["instruction"],
        #
        #     "dependency_results":
        #         state["dependency_results"],
        #
        #     "research_result":
        #         "",
        # })
        # result = specialist_result["research_result"]

    elif state["agent"] == "coder":
        research_input = {
            "query": state["instruction"],
            "draft": "",
            "retry_count": 0,
            "advice": "",
            "code_result": "",
            "dependency_results": state["dependency_results"]
        }
        code_graph = build_code_graph()
        result = code_graph.invoke(research_input)["code_result"]

        # specialist_result = coder({
        #     "query":
        #         state["instruction"],
        #
        #     "dependency_results":
        #         state["dependency_results"],
        #
        #     "code_result":
        #         "",
        # })
        # result = specialist_result["code_result"]

    elif state["agent"] == "writer":
        research_input = {
            "query": state["instruction"],
            "draft": "",
            "retry_count": 0,
            "advice": "",
            "write_result": "",
            "dependency_results": state["dependency_results"]
        }
        write_graph = build_write_graph()
        result = write_graph.invoke(research_input)["write_result"]

        # specialist_result = writer({
        #     "query":
        #         state["instruction"],
        #
        #     "dependency_results":
        #         state["dependency_results"],
        #
        #     "write_result":
        #         "",
        # })
        # result = specialist_result["write_result"]

    else:
        raise ValueError(
            f"Unknown agent: {state['agent']}"
        )

    return {
        "task_results": [
            {
                "work_id":
                    state["work_id"],

                "agent":state["agent"],

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
    advice = state.get("advice","")
    input = f"""
        根据用户需求：{state["query"]}
        完成research工作。
        
        参考资料如下：
        {state["dependency_results"]}
        参考修改意见如下：
        {advice}
    """
    response = researcher_model.invoke(input)
    return {"draft":response.result}

def research_reviewer(state:ResearchState):
    review_model = model.with_structured_output(ResearchReviewOutput)
    review_input = f"""
        根据用户需求{state["query"]}
        判断收集的资料{state["draft"]}
        是否符合要求
        
        如果不符合，给出修改意见：
    """

    review_response = review_model.invoke(review_input)

    try_count = state.get("retry_count", 0)

    if (not review_response.passed) and try_count < 3:
        return Command(
            update={"advice":review_response.advice,
                    "retry_count":try_count+1},
            goto="researcher"
        )
    return Command(
        update={"final_result":state["draft"]},
        goto="research_afterprocess"
    )

def research_afterprocess(state: WriteState|ResearchState|CodingState):

    return {"task_results": [{"result":state["final_result"],
                             "work_id":state["work_id"],
                             "agent":"research"
                             }]
            }

# Coder===============================================================
def coder(state:CodingState):
    coding_model = model.with_structured_output(CodingOutput)
    advice = state.get("advice", "")
    input = f"""
            根据用户需求：{state["query"]}
            完成coding工作。
            参考资料如下：
            {state["dependency_results"]}
            参考修改意见如下：
            {advice}
        """
    response = coding_model.invoke(input)

    return {"draft":response.result}


def coding_reviewer(state: CodingState):
    review_model = model.with_structured_output(CodingReviewOutput)
    review_input = f"""
        根据用户需求{state["query"]}
        判断给出的代码{state["draft"]}
        是否符合要求

        如果不符合，给出修改意见：
    """

    review_response = review_model.invoke(review_input)

    try_count = state.get("retry_count", 0)

    if (not review_response.passed) and try_count < 3:
        return Command(
            update={"advice": review_response.advice,
                    "retry_count": try_count + 1},
            goto="coder"
        )
    return Command(
        update={"final_result":state["draft"]},
        goto="code_afterprocess"
    )

def code_afterprocess(state: WriteState|ResearchState|CodingState):

    return {"task_results": [{"result":state["final_result"],
                             "work_id":state["work_id"],
                             "agent":"coderr"
                             }]
            }
# Writer==============================================================
def writer(state:WriteState):
    writing_model = model.with_structured_output(WriterOutput)
    advice = state.get("advice", "")
    input = f"""
            根据用户需求：{state["query"]}
            完成write工作。
            参考资料如下：
            {state["dependency_results"]}
            参考修改意见如下：
            {advice}
        """
    response = writing_model.invoke(input)

    return {"draft":response.result}


def write_reviewer(state: WriteState):
    review_model = model.with_structured_output(WriteReviewOutput)
    review_input = f"""
        根据用户需求{state["query"]}
        判断生成的回答{state["draft"]}
        是否符合要求

        如果不符合，给出修改意见：
    """

    review_response = review_model.invoke(review_input)

    try_count = state.get("retry_count", 0)

    if (not review_response.passed) and try_count < 3:
        return Command(
            update={"advice": review_response.advice,
                    "retry_count": try_count + 1},
            goto="writer"
        )
    return Command(
        update={"final_result":state["draft"]},
        goto="write_afterprocess"
    )

def write_afterprocess(state: WriteState|ResearchState|CodingState):

    return {"task_results": [{"result":state["final_result"],
                             "work_id":state["work_id"],
                             "agent":"writer"
                             }]
            }
# ========================================================