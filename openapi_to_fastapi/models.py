"""
This module extends some of FastAPI models, to include extra data into them
"""

from typing import Dict, Optional

from fastapi.openapi import models as oas
from pydantic import BaseModel, Field


class Header(oas.Header):
    class Config:
        extra = "ignore"


class ParsedResponse(BaseModel):
    description: Optional[str]
    model_name: Optional[str]


class Operation(oas.Operation):
    requestBodyModel: Optional[str] = ""
    parsedResponses: Dict[int, ParsedResponse] = Field(default_factory=dict)
    headers: Optional[Dict[str, Header]] = None
    deprecated: Optional[bool] = None


class PathItem(oas.PathItem):
    post: Optional[Operation] = None
    get: Optional[Operation] = None
