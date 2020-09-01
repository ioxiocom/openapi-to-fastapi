import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Type

import pydantic
from fastapi import APIRouter

from .model_generator import load_models
from .models import Operation, PathItem
from .parser import parse_openapi_spec
from .validator import BaseValidator
from .validator.core import DefaultValidator


class EmptyModel(pydantic.BaseModel):
    pass


def make_dummy_route(model: Type[pydantic.BaseModel]):
    def _route(request: model):  # type: ignore
        return {}

    return _route


@dataclass
class RoutesMapping:
    default_post: Callable = make_dummy_route
    default_get: Callable = make_dummy_route
    post_map: Optional[Dict[str, Callable]] = None
    get_map: Optional[Dict[str, Callable]] = None


def add_route(
    api_router: APIRouter,
    path: str,
    method: str,
    path_item: PathItem,
    routes: RoutesMapping,
    models_module,
):

    operation: Operation = getattr(path_item, method)
    resp_models = {}
    if operation.responseModels:
        for code, model_name in operation.responseModels.items():
            resp_models[code] = getattr(models_module, model_name)

    router_method = getattr(api_router, method, None)
    if not router_method:
        raise ValueError("Unsupported HTTP method")

    if operation.requestBodyModel:
        model = getattr(models_module, operation.requestBodyModel, None)
    else:
        model = EmptyModel

    routes_map = getattr(routes, f"{method}_map") or {}
    make_route = routes_map.get(path)
    if make_route is None:
        make_route = getattr(routes, f"default_{method}")
    router_method(path)(make_route(model))


def make_router_from_specs(
    specs_path: Path,
    routes: Optional[RoutesMapping] = None,
    validators: List[Type[BaseValidator]] = None,
) -> APIRouter:
    """
    Read OpenAPI specs from the file system and create routes for every endpoint
    found in these specs
    :param specs_path: Path to root directory of OpenAPI specs
    :param routes: Structure pointing to the implementation of the routes
    :param validators: Extra schema validators to run before creating the routes
    :return: Configured APIRouter instance
    """
    api_router = APIRouter()
    validators = validators or []
    validators.insert(0, DefaultValidator)

    for openapi_spec_path in specs_path.glob("**/*.json"):
        validate_spec_and_create_routes(
            api_router, openapi_spec_path, validators, routes
        )
    return api_router


def validate_spec_and_create_routes(
    router: APIRouter,
    spec_path: Path,
    validators: Sequence[Type[BaseValidator]],
    routes: Optional[RoutesMapping] = None,
):
    for validator in validators:
        validator(spec_path).validate()

    raw_spec = spec_path.read_text()
    spec = json.loads(raw_spec)

    routes = routes or RoutesMapping()
    for name, path_item in parse_openapi_spec(spec).items():
        models = load_models(raw_spec, name)
        if path_item.post:
            add_route(router, name, "post", path_item, routes, models)
        if path_item.get:
            add_route(router, name, "get", path_item, routes, models)
