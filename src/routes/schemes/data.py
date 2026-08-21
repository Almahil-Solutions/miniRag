from pydantic import BaseModel, Field
from typing import Optional


class ProcessRequest(BaseModel):
    file_name: Optional[str] = Field(default=None, max_length=255)
    chunk_size: int = Field(default=100, ge=10, le=2000)
    chunk_overlap: int = Field(default=20, ge=0, le=500)
    do_reset: bool = False



