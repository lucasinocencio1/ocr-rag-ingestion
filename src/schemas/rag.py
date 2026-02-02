from typing import Any, Dict, List

from pydantic import BaseModel


class RAGRequest(BaseModel):
    question: str


class RAGResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
