from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: str = "error"
    data: None = None
    details: dict
