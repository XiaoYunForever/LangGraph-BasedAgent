from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

import os
import dotenv

from .state import TaskSpec

dotenv.load_dotenv()

# model = init_chat_model(
#     model="xxx",
#     model_provider="openai",
#     api_key=os.getenv("xxx"),
#     base_url="xxxxxxx"
# )

model = init_chat_model(
    model="qwen3.8-flash",
    model_provider="openai",
    api_key=os.getenv("QWEN_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

class PlannerOutput(BaseModel):
    tasks: list[TaskSpec]

