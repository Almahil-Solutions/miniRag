from pydantic import BaseModel, Field
from typing import Optional
from helpers.config import get_settings

settings = get_settings()


class PushRequest(BaseModel):
    do_reset: bool = False


class SearchRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=50)
    language: Optional[str] = Field(default_factory=lambda: settings.PRIMARY_LANG, max_length=10)
