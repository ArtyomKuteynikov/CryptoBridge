from typing import List

from pydantic import BaseModel


class NodesResponse(BaseModel):
    status: str = "success"
    data: List[str]
    details: dict = {}