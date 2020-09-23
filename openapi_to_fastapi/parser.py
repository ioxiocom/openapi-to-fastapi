from typing import Dict, List, Optional

from fastapi.openapi import models as oas

from .models import Operation, PathItem
from .validator import MissingParameter


def parse_parameters(spec: dict) -> List[oas.Parameter]:
    """
    Create Parameter structure from the OpenAPI spec. Loads what kind of parameters
    are used in the request and which of them are required
    :param spec: Part of an OpenAPI spec for a certain route
    :return: List of Parameter objects
    """
    parameters = []
    for param in spec.get("parameters", []):
        try:
            param_name = param["name"]
        except KeyError:
            raise MissingParameter(f"Name is missing: {param}")
        param_in_ = oas.ParameterInType(param["in"])
        parameter_item = oas.Parameter(**{"name": param_name, "in": param_in_})
        parameter_item.required = param.get("required", False)
        parameter_item.description = param.get("description")
        parameters.append(parameter_item)

    return parameters


def get_model_name_from_ref(spec: dict) -> Optional[str]:
    """
    Get the name of a model schema, which defines a request body or a response.
    Currently only application/json schemas are supported

    :param spec: Part of OpenAPI spec, which defines a model. For example,
    `/paths/<route>/post/requestBody` or `paths/<route>/get/responses/200`
    :return: Model name, for example `BasicCompanyInfoResponse`
    """
    app_json = spec.get("content", {}).get("application/json", {})
    if not app_json:
        return None

    ref_name = app_json.get("schema", {}).get("$ref")
    if ref_name:
        return str(ref_name).split("/")[-1]
    return None


def parse_operation(spec: dict, name: str) -> Optional[Operation]:
    """
    Create Operation structure from the OpenAPI spec. Loads meta information
    like what model defines request/response body of an endpoint
    :param spec: Part of an OpenAPI spec for a certain route
    :param name: Operation name, like "post" or "get"
    :return: Operation item, if it exists
    """

    if not spec.get(name):
        return None

    data = spec[name]
    operation = Operation(responses={}, responseModels={})
    operation.parameters = parse_parameters(spec[name])  # type: ignore

    if data.get("description"):
        operation.description = data.get("description")

    request_body_model = get_model_name_from_ref(data.get("requestBody", {}))
    if request_body_model:
        operation.requestBodyModel = request_body_model

    operation.responseModels = {}
    for resp_code, resp_data in data.get("responses", {}).items():
        code = int(resp_code)
        model_name = get_model_name_from_ref(resp_data)
        if model_name:
            operation.responseModels[code] = model_name

    return operation


def parse_openapi_spec(spec: dict) -> Dict[str, PathItem]:
    """
    Create PathItem structures from the OpenAPI spec. It contains required
    information for setting up routing

    :param spec: OpenAPI spec as dictionary
    :return: Mapping from path to PathItem
    """
    path_items: Dict[str, PathItem] = {}
    for path, data in spec.get("paths", {}).items():
        path_item = PathItem(description=data.get("description"))

        post_operation = parse_operation(data, "post")
        if post_operation:
            path_item.post = post_operation

        get_operation = parse_operation(data, "get")
        if get_operation:
            path_item.get = get_operation

        path_items[path] = path_item

    return path_items
