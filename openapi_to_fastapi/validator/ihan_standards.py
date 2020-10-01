import json
from pathlib import Path

from .core import BaseValidator, OpenApiValidationError


class IhanStandardError(OpenApiValidationError):
    pass


class WrongContentType(IhanStandardError):
    pass


class SchemaMissing(IhanStandardError):
    pass


class NoEndpointsDefined(IhanStandardError):
    pass


class OnlyOneEndpointAllowed(IhanStandardError):
    pass


class PostMethodIsMissing(IhanStandardError):
    pass


class OnlyPostMethodAllowed(IhanStandardError):
    pass


class RequestBodyMissing(IhanStandardError):
    pass


class ResponseBodyMissing(IhanStandardError):
    pass


class AuthorizationHeaderMissing(IhanStandardError):
    pass


class AuthProviderHeaderMissing(IhanStandardError):
    pass


class StandardComponentMissing(IhanStandardError):
    pass


class StandardContentMissing(IhanStandardError):
    pass


class JSONLDError(IhanStandardError):
    pass


def validate_component_schema(spec: dict, components_schema: dict):
    if not spec["content"].get("application/json"):
        raise WrongContentType("Model description must be in application/json format")
    ref = spec["content"]["application/json"].get("schema", {}).get("$ref")
    if not ref:
        raise SchemaMissing(
            'Request or response model is missing from "schema/$ref" section'
        )
    if not ref.startswith("#/components/schemas/"):
        raise SchemaMissing(
            "Request and response models must be defined at"
            '"#/components/schemas/" section'
        )
    model_name = ref.split("/")[-1]
    if not components_schema.get(model_name):
        raise SchemaMissing(f"Component schema is missed for {model_name}")


def validate_spec(spec: dict):
    """
    Validate that OpenAPI spec looks like a standard. For example, that
    it contains only one POST method defined.

    :param spec: OpenAPI spec
    :raises OpenApiValidationError: When OpenAPI spec is incorrect
    """
    paths = spec.get("paths", {})
    if not paths:
        raise NoEndpointsDefined
    if len(paths) > 1:
        raise OnlyOneEndpointAllowed

    post_route = {}
    for name, path in paths.items():
        methods = list(path)
        if "post" not in methods:
            raise PostMethodIsMissing
        if methods != ["post"]:
            raise OnlyPostMethodAllowed
        post_route = path["post"]

    component_schemas = spec.get("components", {}).get("schemas")
    if not component_schemas:
        raise SchemaMissing('No "components/schemas" section defined')

    if post_route.get("requestBody", {}).get("content"):
        validate_component_schema(post_route["requestBody"], component_schemas)

    responses = post_route.get("responses", {})
    if not responses.get("200") or not responses["200"].get("content"):
        raise ResponseBodyMissing
    validate_component_schema(responses["200"], component_schemas)

    headers = [
        param.get("name", "").lower()
        for param in post_route.get("parameters", [])
        if param.get("in") == "header"
    ]
    if "authorization" not in headers:
        raise AuthorizationHeaderMissing
    if "x-authorization-provider" not in headers:
        raise AuthProviderHeaderMissing


def check_extra_files_exist(path: Path):
    html = path.with_suffix(".html")
    if not html.exists():
        raise StandardComponentMissing(f"Missing {html}")
    if html.read_text().strip() == "":
        raise StandardContentMissing(f"Make sure {html} is not empty")

    jsonld = path.with_suffix(".jsonld")
    if not jsonld.exists():
        raise StandardComponentMissing(f"Missing {jsonld}")
    try:
        content = json.loads(jsonld.read_text())
    except json.JSONDecodeError:
        raise JSONLDError(f"Failed to parse {jsonld}")
    else:
        if not content:
            raise StandardContentMissing(f"Make sure {jsonld} is not empty")


class IhanStandardsValidator(BaseValidator):
    def validate_spec(self, spec: dict):
        # just to reduce indentation
        return validate_spec(spec)

    def validate(self):
        super().validate()
        check_extra_files_exist(self.path)
