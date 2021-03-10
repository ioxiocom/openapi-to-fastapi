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


class ServersShouldNotBeDefined(IhanStandardError):
    pass


class SecurityShouldNotBeDefined(IhanStandardError):
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
    if "servers" in spec:
        raise ServersShouldNotBeDefined('"servers" section found')

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

    if "security" in post_route:
        raise SecurityShouldNotBeDefined('"security" section found')

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


class IhanStandardsValidator(BaseValidator):
    def validate_spec(self, spec: dict):
        # just to reduce indentation
        return validate_spec(spec)
