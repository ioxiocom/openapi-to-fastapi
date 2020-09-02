import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Type

import pydantic
from fastapi import APIRouter

from .model_generator import load_models
from .models import Operation
from .parser import parse_openapi_spec
from .validator import BaseValidator
from .validator.core import DefaultValidator


class EmptyModel(pydantic.BaseModel):
    pass


def make_dummy_route(
    request_model: Type[pydantic.BaseModel], response_model: Type[pydantic.BaseModel]
):
    def _route(request: request_model):  # type: ignore
        return {}

    return _route


@dataclass
class RouteInfo:
    factory: Callable = make_dummy_route
    name: Optional[str] = None
    name_factory: Optional[Callable] = None
    description: Optional[str] = None
    response_description: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class RoutesMapping:
    default_post: RouteInfo = RouteInfo()
    default_get: RouteInfo = RouteInfo()
    post_map: Optional[Dict[str, RouteInfo]] = None
    get_map: Optional[Dict[str, RouteInfo]] = None


def add_route(
    api_router: APIRouter,
    path: str,
    method: str,
    operation: Operation,
    routes: RoutesMapping,
    models_module,
):

    resp_model = None
    if operation.responseModels and operation.responseModels.get(200):
        resp_model = getattr(models_module, operation.responseModels[200])

    router_method = getattr(api_router, method, None)
    if not router_method:
        raise ValueError("Unsupported HTTP method")

    if operation.requestBodyModel:
        request_model = getattr(models_module, operation.requestBodyModel, None)
    else:
        request_model = EmptyModel

    routes_map = getattr(routes, f"{method}_map") or {}
    route_info: Optional[RouteInfo] = routes_map.get(path)
    if route_info is None:
        route_info = getattr(routes, f"default_{method}")

    route_name = route_info.name
    if route_info.name_factory:
        route_name = route_info.name_factory(path=path, operation=operation)

    router_method(
        path,
        response_model=resp_model,
        name=route_name,
        description=route_info.description or operation.description,
        tags=route_info.tags,
        response_description=route_info.response_description,
    )(route_info.factory(request_model, resp_model))


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
            add_route(router, name, "post", path_item.post, routes, models)
        if path_item.get:
            add_route(router, name, "get", path_item.get, routes, models)
