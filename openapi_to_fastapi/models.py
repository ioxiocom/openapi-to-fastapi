"""
This module extends some of FastAPI models, to include extra data into them
"""

from typing import Dict, Optional

from fastapi.openapi import models as oas
from pydantic import BaseModel, ConfigDict, Field


class Header(oas.Header):
    model_config = ConfigDict(extra="ignore")


class ParsedResponse(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None


class Operation(oas.Operation):
    requestBodyModel: Optional[str] = ""
    parsedResponses: Dict[int, ParsedResponse] = Field(default_factory=dict)
    headers: Optional[Dict[str, Header]] = None
    deprecated: Optional[bool] = None


class PathItem(oas.PathItem):
    post: Optional[Operation] = None
    get: Optional[Operation] = None
