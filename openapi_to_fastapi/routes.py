import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

import pydantic
from fastapi import APIRouter

from .model_generator import load_models
from .parser import parse_openapi_spec
from .utils import add_annotation_to_first_argument, copy_function
from .validator.core import BaseValidator, DefaultValidator


def dummy_route(request):
    """
    Default handler to use if nothing was provided by user
    :param request: Incoming request
    :return: Empty JSON response
    """
    return {}


class EmptyBody(pydantic.BaseModel):
    pass


@dataclass
class RouteInfo:
    description: Optional[str] = None
    name: Optional[str] = None
    name_factory: Optional[Callable] = None
    response_description: str = "Successful response"
    tags: Optional[List[str]] = None

    request_model: Optional[Type[pydantic.BaseModel]] = None
    response_model: Optional[Type[pydantic.BaseModel]] = None
    responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None
    handler: Callable = dummy_route

    def merge_with(self, another_route: "RouteInfo"):
        for v in vars(self).keys():
            another_value = getattr(another_route, v)
            if another_value is not None:
                setattr(self, v, another_value)


@dataclass
class RoutesMapping:
    default_get: RouteInfo = RouteInfo()
    default_post: RouteInfo = RouteInfo()
    get_map: Optional[Dict[str, RouteInfo]] = None
    post_map: Optional[Dict[str, RouteInfo]] = None


class SpecRouter:
    def __init__(
        self,
        specs_path: Union[str, Path],
        validators: List[Type[BaseValidator]] = None,
    ):
        self._validators = [DefaultValidator] + (validators or [])  # type: ignore
        self._routes = RoutesMapping(post_map={}, get_map={})

        self.specs_path = Path(specs_path)
        self._validate_and_parse_specs()

    def _validate_and_parse_specs(self):
        """
        Validate OpenAPI specs and parse required information from them
        """
        if self.specs_path.is_file():
            specs = [self.specs_path]  # for CLI usage
        else:
            specs = self.specs_path.glob("**/*.json")

        for spec_path in specs:
            for validator in self._validators:
                validator(spec_path).validate()

            raw_spec = spec_path.read_text(encoding="utf8")
            json_spec = json.loads(raw_spec)
            for path, path_item in parse_openapi_spec(json_spec).items():
                models = load_models(raw_spec, path)
                post = path_item.post
                if post:
                    req_model = getattr(models, post.requestBodyModel, EmptyBody)
                    route_info = RouteInfo(
                        request_model=req_model, description=post.description
                    )
                    if post.responseModels and post.responseModels.get(200):
                        resp_model = getattr(models, post.responseModels[200])
                        route_info.response_model = resp_model
                    self._routes.post_map[path] = route_info

    def get_response_model(
        self, path: str, method: str
    ) -> Optional[Type[pydantic.BaseModel]]:
        """
        Get response model for a specific path
        :param path: Path of the route, e.g "/pets"
        :param method: HTTP Method, e.g "post" or "GET"
        :return: Pydantic model with the fields defined in spec
        """
        store = getattr(self._routes, f"{method.lower()}_map", None)
        if store is None:
            raise ValueError("Unsupported HTTP method")
        route_info: RouteInfo = store.get(path)
        if not route_info:
            return None
        return route_info.response_model

    def post(
        self,
        path: Optional[str] = None,
        name: str = None,
        tags: List[str] = None,
        description: str = None,
        response_description: str = None,
        name_factory: Optional[Callable] = None,
        responses: Dict[Union[int, str], Dict[str, Any]] = None,
    ):
        """
        Define implementation for a specific POST route
        If path argument is not provided, then this handler will be used in all POST
        routes found in the OpenAPI spec
        :param path: Path of the route, e.g "/pets"
        :param name: Name of the route, mainly used in docs
        :param name_factory: Function to generate route name from path.
            It has precedence over `name` param
        :param tags: Specific tags for docs
        :param description: Route description. Got from OpenAPI spec by default
        :param response_description: Description of the response
        :param responses: Possible responses the route may return. Used in documentation
        """

        def _wrapper(fn):
            if path is None:
                route_info = RouteInfo()
                self._routes.default_post = route_info
            else:
                route_info = self._routes.post_map[path]

            route_info.handler = fn
            route_info.name = name
            route_info.tags = tags
            route_info.name_factory = name_factory
            route_info.responses = responses

            if response_description:
                route_info.response_description = response_description
            if description:
                route_info.description = description

            return fn

        return _wrapper

    def to_fastapi_router(self):
        """
        Creates an instance of FastAPI router. Must be called after route definitions
        :return: APIRouter instance
        """
        router = APIRouter()

        # POST methods
        for path, route_info in self._routes.post_map.items():
            resp_model = self.get_response_model(path, "post")
            req_model = route_info.request_model

            # if route is not customized, fall back to default POST
            if route_info.handler == dummy_route:
                route_info.merge_with(self._routes.default_post)

            route_name = route_info.name
            if route_info.name_factory:
                route_name = route_info.name_factory(path)

            handler = copy_function(route_info.handler)
            add_annotation_to_first_argument(handler, req_model)  # noqa type: ignore

            router.post(
                path,
                name=route_name,
                summary=route_name,
                description=route_info.description,
                response_description=route_info.response_description,
                response_model=resp_model,
                responses=route_info.responses,
                tags=route_info.tags,
            )(handler)
        return router
