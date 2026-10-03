from langgraph.types import Send
# from langgraph.runtime import Runtime
# from langgraph.types import Command
from .state import *

def planner(state:OverallState):
    planner_model = model.with_structured_output(PlannerOutput)
    inputt = f"""
        你是一个多智能体任务规划器（Planner）。
        
        你的职责是：
        根据用户的总体目标，将任务拆分为若干清晰、可执行的子任务，并建立合理的依赖关系，
        供后续 Research Agent、Coding Agent 和 Writer Agent 执行。
        
        【用户总体目标】
        {state["goal"]}
        
        【可用 Agent】
        
        research：
        负责资料收集、知识整理、事实分析、概念解释和技术调研。
        
        coder：
        负责编写、修改、分析或解释代码，并生成可直接使用的实现结果。
        
        writer：
        负责整合已有结果，生成最终面向用户的自然语言回答。
        
        【任务规划原则】
        
        1. 每个子任务只完成一个明确目标，避免把多个不同工作混在同一个任务中。
        
        2. 只创建完成用户目标真正需要的任务。
        不要为了使用所有 Agent 而强行创建 research、coder 或 writer 任务。
        
        3. 能并行执行的任务不要设置依赖。
        只有当任务 B 确实需要任务 A 的结果才能执行时，B 才依赖 A。
        
        4. work_id 必须唯一、简洁、稳定。
        建议使用：
        research_1
        code_1
        write_1
        等形式。
        
        5. depends_on 中只能出现本次计划中真实存在的 work_id。
        
        6. 禁止：
        - 依赖不存在的 work_id
        - 自己依赖自己
        - 循环依赖
        
        7. instruction 必须描述该 Agent 自己应该完成的工作，
        不要在 instruction 中写 {{research_1}}、{{code_1}} 等结果占位符。
        上游任务的真实结果会由系统通过 dependency_results 自动提供。
        
        8. 如果最终需要把多个子任务结果组合成用户回答，
        可以创建 writer 任务，并让它依赖真正需要整合的上游任务。
        
        9. 不要让 Writer 重复执行 Research 或 Coding 已经完成的工作。
        Writer 的主要职责是筛选、组织和整合已有结果。
        
        10. 优先生成最小、清晰、高并行度的任务 DAG，
        避免没有必要的任务和依赖。
        
        【规划前自检】
        
        生成计划前，请确保：
        - 所有 work_id 唯一；
        - 每个 depends_on 都指向真实存在的 work_id；
        - DAG 中不存在循环；
        - 没有不必要的串行依赖；
        - 所有必要结果最终都能被后续任务消费；
        - 整个任务集合足以完成用户总体目标。
        
        只生成符合 PlannerOutput 结构的任务计划。
        不要输出任务计划之外的解释。
        """
    plan = planner_model.invoke(inputt)

    return {
        "tasks": plan.tasks
    }

from collections import Counter, deque
from langgraph.types import Command


def validate_plan(tasks: list[TaskSpec]) -> list[str]:
    """
    校验 Planner 生成的任务 DAG。

    返回：
        []          -> 合法
        [error,...] -> 非法原因
    """

    errors: list[str] = []

    # ============================================================
    # 1. 检查 work_id 是否唯一
    # ============================================================

    work_ids = [
        task["work_id"]
        for task in tasks
    ]

    counter = Counter(work_ids)

    duplicated_ids = [
        work_id
        for work_id, count in counter.items()
        if count > 1
    ]

    if duplicated_ids:
        errors.append(
            f"存在重复的 work_id: {duplicated_ids}"
        )


    # 如果 work_id 本身已经重复，
    # 后面的 DAG 建图语义就不可靠，
    # 但我们仍然可以继续检查部分基础错误。
    work_id_set = set(work_ids)


    # ============================================================
    # 2. 检查 depends_on 是否存在
    # 3. 检查 self dependency
    # ============================================================

    for task in tasks:

        for dependency_id in task["depends_on"]:

            # ---- dependency 必须存在 ----
            if dependency_id not in work_id_set:

                errors.append(
                    f"任务 {task["work_id"]} "
                    f"依赖不存在的任务 "
                    f"{dependency_id}"
                )

            # ---- 不能依赖自己 ----
            if dependency_id == task["work_id"]:

                errors.append(
                    f"任务 {task["work_id"]} "
                    f"不能依赖自身"
                )


    # ============================================================
    # 4. 检查循环依赖
    #
    # 只有基础结构没有问题时才做拓扑排序，
    # 否则不存在的 dependency / duplicate id
    # 会让 DAG 图本身含义不明确。
    # ============================================================

    if not errors:

        # dependency -> task
        #
        # 例如：
        #
        # research_1 -> write_1
        # code_1     -> write_1

        adjacency: dict[str, list[str]] = {
            work_id: []
            for work_id in work_ids
        }

        indegree: dict[str, int] = {
            work_id: 0
            for work_id in work_ids
        }


        for task in tasks:

            for dependency_id in task["depends_on"]:

                adjacency[dependency_id].append(
                    task["work_id"]
                )

                indegree[task["work_id"]] += 1


        # 所有入度为 0 的任务都可以作为 DAG 起点
        queue = deque(
            work_id
            for work_id, degree
            in indegree.items()
            if degree == 0
        )


        visited_count = 0

        while queue:

            current = queue.popleft()

            visited_count += 1

            for next_task in adjacency[current]:

                indegree[next_task] -= 1

                if indegree[next_task] == 0:
                    queue.append(next_task)


        # DAG 中如果没有环，
        # 拓扑排序一定可以访问全部节点。
        if visited_count != len(work_ids):

            cycle_nodes = [
                work_id
                for work_id, degree
                in indegree.items()
                if degree > 0
            ]

            errors.append(
                f"任务依赖关系存在循环依赖，"
                f"涉及任务: {cycle_nodes}"
            )


    return errors

def plan_validator(state: OverallState):

    errors = validate_plan(
        state["tasks"]
    )

    # ============================================================
    # 非法计划
    # ============================================================

    if errors:

        error_message = (
            "Planner 生成的任务计划不合法：\n- "
            + "\n- ".join(errors)
        )

        return Command(
            update={
                "error": error_message
            },
            goto="dependency_error"
        )


    # ============================================================
    # 合法计划
    # ============================================================

    return Command(
        update={
            "error": ""
        },
        goto="Scheduler"
    )


def Scheduler(state:OverallState):
    all_finished_tasks = {
        task["work_id"]
        for task in state["task_results"]
    }

    remaining_tasks = [
        task
        for task in state["tasks"]
        if task["work_id"]
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
            task["depends_on"]
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
               in task["depends_on"]
        }
        if task["agent"] == "research":
            sends.append(
                Send(
                    "researcher",
                    {
                        "work_id":
                            task["work_id"],

                        "query":
                            task["instruction"],

                        "dependency_results":
                            dependency_results,
                    }
                )
            )
        elif task["agent"] == "coder":
            sends.append(
                Send(
                    "coder",
                    {
                        "work_id":
                            task["work_id"],

                        "query":
                            task["instruction"],

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
                            task["work_id"],

                        "query":
                            task["instruction"],

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
        你是项目中的 Research Agent，负责为后续子任务收集、整理和提炼必要的信息。
        
        【当前子任务】
        {state["query"]}
        
        【上游依赖结果】
        {state["dependency_results"]}
        
        【Reviewer 修改意见】
        {advice}
        
        请完成当前 research 子任务，并遵循以下要求：
        
        1. 只研究当前子任务要求的内容，不扩展到无关主题。
        2. 如果存在上游依赖结果，应将其作为已有上下文使用，避免重复工作。
        3. 如果 Reviewer 提供了修改意见，应优先解决修改意见指出的问题。
        4. 提炼对下游 Agent 真正有用的信息，避免冗长背景介绍。
        5. 对不确定的信息不要编造；如果缺少必要信息，应明确指出。
        6. 输出应具有清晰的逻辑结构，使 coder 或 writer 可以直接使用。
        
        最终只输出本次 research 的研究结果，不要描述你的思考过程，也不要说明你是 Research Agent。
        """
    response = researcher_model.invoke(input)
    return {"draft":response.result}

def research_reviewer(state:ResearchState):
    review_model = model.with_structured_output(ResearchReviewOutput)
    review_input =  f"""
        你是 Research Agent 的 Reviewer。
        
        【任务要求】
        {state["query"]}
        
        【当前结果】
        {state["draft"]}
        
        请判断当前结果是否足以完成该 research 子任务。
        
        重点检查：
        - 是否回答了任务要求的核心问题；
        - 是否存在明显遗漏、错误或无关内容；
        - 内容是否足够清晰，可供下游 Agent 直接使用；
        - 是否存在无依据的结论或明显矛盾。
        
        如果已经满足要求：
        passed = true
        advice = ""
        
        如果不满足要求：
        passed = false
        advice = 给出具体、可执行的修改意见，明确指出需要补充、删除或修正什么。
        
        不要重新完成 research 任务，只负责审核。
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
        你是项目中的 Coding Agent，负责根据当前任务生成正确、清晰、可执行的代码。
        
        【当前子任务】
        {state["query"]}
        
        【上游依赖结果】
        {state["dependency_results"]}
        
        【Reviewer 修改意见】
        {advice}
        
        请完成当前 coding 子任务，并遵循以下要求：
        
        1. 严格围绕当前子任务编写代码，不实现无关功能。
        2. 如果存在上游 research 结果，应提取其中与实现相关的约束、算法和注意事项。
        3. 如果 Reviewer 提供了修改意见，应优先修复对应问题。
        4. 保证代码逻辑完整，变量命名清晰，并处理任务明确要求的边界情况。
        5. 除非任务明确要求，否则避免不必要的框架、依赖和复杂设计。
        6. 必要时添加简洁注释和最小测试示例。
        7. 不要只描述“应该如何实现”，必须给出实际实现结果。
        
        最终输出应以可直接使用的代码为核心，可以附带极少量必要说明。
        不要输出你的思考过程。
        """
    response = coding_model.invoke(input)

    return {"draft":response.result}


def coding_reviewer(state: CodingState):
    review_model = model.with_structured_output(CodingReviewOutput)
    review_input = f"""
        你是 Coding Agent 的代码 Reviewer。
        
        你的职责不是重新完成 Coding 任务，
        而是检查 Coding Agent 当前生成的结果是否已经满足任务要求，
        并决定通过或要求修改。
        
        【Coding 子任务】
        {state["query"]}
        
        【Coding Agent 当前结果】
        {state["draft"]}
        
        请从以下方面进行审核：
        
        1. 任务完成度
        检查代码是否真正实现了当前 Coding 子任务要求，
        是否存在遗漏的重要功能。
        
        2. 正确性
        检查核心算法、控制流程、条件判断、返回值和数据处理是否存在明显错误。
        
        3. 可执行性
        如果任务要求可运行代码，检查代码是否基本完整，
        是否存在明显的语法错误、未定义变量或缺失的关键实现。
        
        4. 输入输出
        检查函数参数、返回值以及数据结构是否符合任务要求。
        
        5. 边界情况
        检查任务中明确要求的边界情况是否被合理处理。
        不要为了追求完美而强制加入任务没有要求的复杂逻辑。
        
        6. 简洁性
        避免明显的过度设计、无意义依赖或与任务无关的实现。
        
        【判定规则】
        
        只有存在会明显影响任务正确完成的问题时，才判定为不通过。
        不要因为代码风格偏好、变量名的小差异或非必要优化而反复驳回。
        
        如果结果已经满足任务要求：
        passed = true
        advice = ""
        
        如果结果不满足要求：
        passed = false
        
        advice 必须：
        - 具体；
        - 可执行；
        - 明确指出哪里有问题；
        - 明确说明下一次应该修改什么。
        
        不要在 advice 中重新给出完整代码，
        不要输出你的思考过程。
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
                             "agent":"coder"
                             }]
            }
# Writer==============================================================
def writer(state:WriteState):
    writing_model = model.with_structured_output(WriterOutput)
    advice = state.get("advice", "")
    input = f"""
        你是项目中的 Writer Agent，负责将已有子任务结果整合为最终面向用户的回答。
        
        【当前写作任务】
        {state["query"]}
        
        【已有子任务结果】
        {state["dependency_results"]}
        
        【Reviewer 修改意见】
        {advice}
        
        请完成最终回答，并遵循以下要求：
        
        1. 优先使用 dependency_results 中已经完成的 research、coding 或其他子任务结果。
        2. 不要无意义地重复上游 Agent 的工作，而是对已有结果进行筛选、组织和整合。
        3. 确保最终回答直接满足当前写作任务以及原始用户需求。
        4. 如果多个上游结果存在重复内容，应合并而不是重复罗列。
        5. 如果上游结果存在明显冲突，应采用逻辑一致、能够满足任务要求的内容。
        6. 如果 Reviewer 提供修改意见，应优先修正这些问题。
        7. 保持回答结构清晰、内容完整，但避免不必要的冗长。
        8. 如果包含代码，应完整保留代码的关键实现，不要只给伪代码或描述。
        
        最终只输出可以直接呈现给用户的回答。
        不要提及 Research Agent、Coding Agent、dependency_results 或内部工作流程，也不要输出你的思考过程。
        """
    response = writing_model.invoke(input)

    return {"draft":response.result}


def write_reviewer(state: WriteState):
    review_model = model.with_structured_output(WriteReviewOutput)
    review_input = f"""
        你是 Writer Agent 的最终回答 Reviewer。
        
        你的职责是检查 Writer Agent 当前生成的回答，
        判断它是否已经可以直接作为最终结果呈现给用户。
        
        你不负责重新撰写完整回答，只负责审核并给出必要的修改意见。
        
        【当前写作任务】
        {state["query"]}
        
        【Writer 当前回答】
        {state["draft"]}
        
        请从以下方面审核：
        
        1. 用户需求覆盖
        检查当前回答是否直接完成了写作任务要求，
        是否遗漏用户明确要求的内容。
        
        2. 内容正确性
        检查回答中是否存在与上游可靠结果明显矛盾的内容，
        以及明显的事实、逻辑或技术错误。
        
        3. 信息整合
        检查 Writer 是否真正进行了整理和整合，
        而不是简单把多个 Agent 输出机械拼接在一起。
        
        4. 代码完整性
        如果最终回答应该包含代码，
        检查关键代码是否完整保留，
        不能只描述代码而遗漏实际实现。
        
        5. 内部信息泄露
        最终回答中不应出现：
        - Research Agent
        - Coding Agent
        - Writer Agent
        - dependency_results
        - work_id
        - Scheduler
        - Reviewer
        等内部执行流程信息，
        除非用户明确要求了解 Agent 工作过程。
        
        6. 避免无关扩展
        不要因为可以补充更多知识，就要求 Writer 增加用户没有需要的大量背景内容。
        
        【判定规则】
        
        如果回答已经能够直接满足用户需求，即可通过。
        不要因为轻微措辞、个人写作偏好或非必要扩展而判定失败。
        
        如果满足要求：
        passed = true
        advice = ""
        
        如果不满足要求：
        passed = false
        
        advice 必须明确指出：
        - 哪部分存在问题；
        - 为什么影响用户需求；
        - 下一次应该如何修改。
        
        修改意见应简洁、具体、可执行。
        不要重新生成完整最终回答，
        不要输出你的思考过程。
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