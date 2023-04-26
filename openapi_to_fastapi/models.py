"""
This module extends some of FastAPI models, to include extra data into them
"""

from typing import Dict, Optional

from fastapi.openapi import models as oas


class Header(oas.Header):
    class Config:
        extra = "ignore"


class Operation(oas.Operation):
    requestBodyModel: Optional[str] = ""
    responseModels: Optional[Dict[int, str]] = None
    headers: Optional[Dict[str, Header]] = None


class PathItem(oas.PathItem):
    post: Optional[Operation] = None
    get: Optional[Operation] = None
