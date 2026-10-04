import operator
from pydantic import BaseModel, Field
from typing import Annotated
from typing_extensions import NotRequired
from typing_extensions import TypedDict
from typing import Literal
from .model import *



class TaskSpec(TypedDict):

    work_id: str

    agent: Literal[
    "research",
    "coder",
    "writer",
]

    instruction: str

    depends_on: list[str]

class PlannerOutput(BaseModel):
    tasks: list[TaskSpec]

class TaskResult(TypedDict):

    work_id: str

    agent:str

    result: str


class WorkerState(TypedDict):

    work_id: str

    agent: str

    instruction: str

    dependency_results:dict[str, str]


class OverallState(TypedDict):

    goal: str

    tasks: list[TaskSpec]

    task_results: Annotated[
        list[TaskResult],
        operator.add
    ]

    final_answer: str

    wave: int

    error: str

    approval_status: NotRequired[
        Literal["pending", "approved", "rejected"]
    ]

    # 区分计划来源
    plan_origin: NotRequired[
        Literal["planner", "human"]
    ]

    # 保存校验错误，供下一次人工编辑使用
    validation_errors: NotRequired[list[str]]


# Researcher==========================================================
class ResearchOutput(BaseModel):
    result:str

class ResearchReviewOutput(BaseModel):
    passed:bool=Field(description="内容是否符合用户要求")

    advice:str=Field(description="如果不通过，有什么修改意见。")

class ResearchState(TypedDict):

    query:str

    draft:str

    retry_count:int

    advice:str

    final_result:str

    dependency_results: dict[str, str]

    work_id:str

    task_results: Annotated[
        list[TaskResult],
        operator.add
    ]

# Coder===============================================================
class CodingOutput(BaseModel):
    result: str

class CodingReviewOutput(BaseModel):
    passed:bool=Field(description="内容是否符合用户要求")

    advice:str=Field(description="如果不通过，有什么修改意见。")

class CodingState(TypedDict):

    query:str

    draft: str

    retry_count: int

    advice: str

    final_result:str

    dependency_results: dict[str, str]

    work_id: str

    task_results: Annotated[
        list[TaskResult],
        operator.add
    ]

# Writer==============================================================
class WriterOutput(BaseModel):
    result:str

class WriteReviewOutput(BaseModel):
    passed:bool=Field(description="内容是否符合用户要求")

    advice:str=Field(description="如果不通过，有什么修改意见。")

class WriteState(TypedDict):

    query:str

    draft: str

    retry_count: int

    advice: str

    final_result:str

    dependency_results: dict[str, str]

    work_id: str

    task_results: Annotated[
        list[TaskResult],
        operator.add
    ]

# ===========================================
class SubAgentInput(TypedDict):
    work_id: str
    query: str
    dependency_results: dict[str, str]

class SubAgentOutput(TypedDict):
    task_results: Annotated[
        list[TaskResult],
        operator.add
    ]