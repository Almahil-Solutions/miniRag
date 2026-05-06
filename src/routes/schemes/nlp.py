from pydantic import BaseModel
from typing import Optional
from helpers.config import get_settings

settings = get_settings()


class PushRequest(BaseModel):
    do_reset: Optional[int] = 0

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    # PRIMARY_LANG from .env file 
    language: Optional[str] = settings.PRIMARY_LANG
