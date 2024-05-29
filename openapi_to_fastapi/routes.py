import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union

import pydantic
from fastapi import APIRouter, params
from fastapi.openapi import models as oas

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
    summary: Optional[str] = None
    deprecated: Optional[bool] = None
    dependencies: Optional[Sequence[params.Depends]] = None

    request_model: Optional[Type[pydantic.BaseModel]] = None
    response_model: Optional[Type[pydantic.BaseModel]] = None
    responses: Optional[Dict[int, Dict[str, Any]]] = None
    headers: Dict[str, oas.Header] = field(default_factory=dict)
    handler: Callable = dummy_route

    def merge_with(self, another_route: "RouteInfo"):
        for v in vars(self).keys():
            another_value = getattr(another_route, v)
            if another_value is not None:
                setattr(self, v, another_value)

    def get_additional_response_models(self) -> Dict[int, Type[pydantic.BaseModel]]:
        """
        Get a mapping of additional response code to model.

        :return: A mapping of a status code to a Pydantic model with the fields defined
        in the spec.
        """

        if not self.responses:
            return {}
        return {
            status: additional_response_data["model"]
            for status, additional_response_data in self.responses.items()
            if self.responses and "model" in additional_response_data
        }


@dataclass
class RoutesMapping:
    default_get: RouteInfo = field(default_factory=RouteInfo)
    default_post: RouteInfo = field(default_factory=RouteInfo)
    get_map: Optional[Dict[str, RouteInfo]] = None
    post_map: Optional[Dict[str, RouteInfo]] = None


class SpecRouter:
    def __init__(
        self,
        specs_path: Union[str, Path],
        validators: Optional[List[Type[BaseValidator]]] = None,
        format_code: bool = False,
        cleanup: bool = True,
    ):
        self._validators = [DefaultValidator] + (validators or [])  # type: ignore
        self._routes = RoutesMapping(post_map={}, get_map={})
        self._format_code = format_code

        self.specs_path = Path(specs_path)
        self._validate_and_parse_specs(cleanup)

    @property
    def get_map(self) -> Optional[Dict[str, RouteInfo]]:
        """
        Get a mapping of parsed paths to route info for GET routes.
        """
        return self._routes.get_map

    @property
    def post_map(self) -> Optional[Dict[str, RouteInfo]]:
        """
        Get a mapping of parsed paths to route info for POST routes.
        """
        return self._routes.post_map

    def _validate_and_parse_specs(self, cleanup=True):
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
                models = load_models(
                    raw_spec, path, cleanup=cleanup, format_code=self._format_code
                )
                post = path_item.post
                if post:
                    req_model = getattr(models, post.requestBodyModel, EmptyBody)
                    route_info = RouteInfo(
                        request_model=req_model,
                        description=post.description,
                        tags=post.tags,
                        summary=post.summary,
                        headers=post.headers,
                        deprecated=post.deprecated,
                        responses={},
                    )

                    for status_code, parsed_response in post.parsedResponses.items():
                        resp_model = getattr(models, parsed_response.name)
                        description = parsed_response.description
                        if status_code == 200:
                            route_info.response_model = resp_model
                        else:
                            # An entry for an additional response for FastAPI routes
                            # https://fastapi.tiangolo.com/advanced/additional-responses/#additional-response-with-model
                            additional_response = {}
                            if parsed_response.description:
                                additional_response["description"] = description
                            if parsed_response.name:
                                additional_response["model"] = resp_model

                            route_info.responses[status_code] = additional_response

                    self._routes.post_map[path] = route_info

    def get_route_info(self, path: str, method: str) -> Optional[RouteInfo]:
        """
        Get the RouteInfo for a specific path and method
        :param path: Path of the route, e.g "/pets"
        :param method: HTTP Method, e.g "post" or "GET"
        :return: The corresponding RouteInfo.
        """
        store = getattr(self._routes, f"{method.lower()}_map", None)
        if store is None:
            raise ValueError("Unsupported HTTP method")
        route_info: Optional[RouteInfo] = store.get(path)
        return route_info

    def get_response_model(
        self, path: str, method: str
    ) -> Optional[Type[pydantic.BaseModel]]:
        """
        Get response model for a specific path
        :param path: Path of the route, e.g "/pets"
        :param method: HTTP Method, e.g "post" or "GET"
        :return: Pydantic model with the fields defined in spec
        """
        route_info = self.get_route_info(path=path, method=method)
        if not route_info:
            return None
        return route_info.response_model

    def post(
        self,
        path: Optional[str] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        response_description: Optional[str] = None,
        name_factory: Optional[Callable] = None,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
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
        :param dependencies: Possible dependencies to add to the route.
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
            route_info.dependencies = dependencies

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
                summary=route_info.summary or route_name,
                description=route_info.description,
                response_description=route_info.response_description,
                response_model=resp_model,
                responses=route_info.responses,
                tags=route_info.tags,
                deprecated=route_info.deprecated,
                dependencies=route_info.dependencies,
            )(handler)
        return router
