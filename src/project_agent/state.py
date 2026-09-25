import operator
from pydantic import BaseModel, Field
from typing import Annotated
from typing_extensions import TypedDict
from typing import Literal

class TaskSpec(BaseModel):

    work_id: str

    agent: Literal[
    "research",
    "coder",
    "writer",
]

    instruction: str

    depends_on: list[str] = Field(
    default_factory=list,
    description=(
        "当前任务依赖的其他work_id。"
        "无依赖时返回空列表。"
    )
)


class TaskResult(TypedDict):

    work_id: str

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



# Researcher==========================================================
class ResearchOutput(BaseModel):
    result:str

class ResearchState(TypedDict):

    query:str

    research_result:str

    dependency_results: dict[str, str]



# Coder===============================================================
class CodingOutput(BaseModel):
    result: str

class CodingState(TypedDict):

    query:str

    code_result:str

    dependency_results: dict[str, str]



# Writer==============================================================
class WriterOutput(BaseModel):
    result:str

class WriteState(TypedDict):

    query:str

    write_result:str

    dependency_results: dict[str, str]
