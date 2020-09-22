"""
This module extends some of FastAPI models, to include extra data into them
"""

from typing import Dict, Optional

from fastapi.openapi import models as oas


class Operation(oas.Operation):
    requestBodyModel: Optional[str] = ""
    responseModels: Optional[Dict[int, str]] = None


class PathItem(oas.PathItem):
    post: Optional[Operation] = None
    get: Optional[Operation] = None
