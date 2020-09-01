## The reasoning

There's an awesome [FastAPI](https://github.com/tiangolo/fastapi) library which simplifies the process of creating APIs.
The one of the most exciting parts of it is the generation of OpenAPI specs out of the box.
But what if.. you have an OpenAPI spec and you need to create an API from it?

One day we met such problem — the need of creating an API from a multiple OpenAPI specs,
and to make sure that requests which comes in and the responses which comes out are aligned
with the models defined in those specs.

> ⚠️ This library was created with an idea to cover only our needs first.
> So for now it's not suitable for everyone and has a lot of technical restrictions.
> Please consider it as an experimental stuff

## Installation

The package is available on PyPi:

```bash
pip install openapi-to-fastapi
```

## FastAPI routes generation

The main purpose of this library is to generate FastAPI routes from the OpenAPI specs.
This is done by:

```python
from pathlib import Path
from openapi_to_fastapi.routes import make_router_from_specs

specs = Path("./specs")

router = make_router_from_specs(specs)
```

The code above will generate FastAPI router which then can be included into the main router,
or just be used as the default one.

Imagine you have a following spec (some parts are cut off for brevity):

```json
{
  "openapi": "3.0.2",
   ...
  "paths": {
    "/Company/BasicInfo": {
      "post": {
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BasicCompanyInfoRequest"
    ...
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/BasicCompanyInfoResponse"

    ...
  },
  "components": {
    "schemas": {
      "BasicCompanyInfoRequest": {
        "title": "BasicCompanyInfoRequest",
        "required": ["companyId"],
        "type": "object",
        "properties": {
          "companyId": {
            "title": "Company Id",
            "type": "string",
            "example": "2464491-9"
          }
        }
      },
      "BasicCompanyInfoResponse": {
        "title": "BasicCompanyInfoResponse",
        "required": ["name", "companyId", "companyForm"],
        "type": "object",
        "properties": {
          "name": {
            "title": "Name of the company",
            "type": "string",
          },
          "companyId": {
            "title": "ID of the company",
            "type": "string",
          },
          "companyForm": {
            "title": "The company form of the company",
            "type": "string",
          },
```

The FastAPI route equivalent could look like:

```python
class BasicCompanyInfoRequest(pydantic.BaseModel):
    companyId: str

class BasicCompanyInfoResponse(pydantic.BaseModel):
    name: str
    companyId: str
    companyForm: str


@router.post("/Company/BasicInfo", response_model=BasicCompanyInfoResponse)
def _route(request: BasicCompanyInfoRequest):
    return {}

```

And the `openapi-to-fastapi` is in charge of creating it automagically.

### Custom routes

In most cases it makes no sense to create an API without any business logic.

Here's how to define it:

```python
# Define a function which returns an usual valid FastAPI route.
# It takes 2 pydantic models as arguments — defining request and response bodies
def default_post_route(request_model, response_model):

    def _route(request: request_model, x_my_token: str = Header(...)):
        if x_my_token != "my_token":
            raise HTTPException(status_code=403, detail="Sorry")
        return {"Hello": "World"}

    return _route

def create_pet(request_model, response_model):

    # imagine line @router.post("/pet", response_model=response_model) here
    def _route(request: request_model):
        pet = db.make_pet(name=request.name)
        return pet.to_dict()

    return _route


from openapi_to_fastapi.routes import RoutesMapping, RouteInfo

routes = RoutesMapping(
        # all POST routes found in the spec will be created with this default handler
        default_post=RouteInfo(factory=default_post_route),
        # custom handlers for POST methods
        post_map={
            # custom handler for POST method to /pet
            "/pet": RouteInfo(factory=create_pet)
        }
    )
router = make_router_from_specs(specs, routes)
```

### API Documentation

Now after you have a lot of routes, you might want to leverage another great feature of
FastAPI — auto documentation.

Request and response models are already handled. But to display documentation nicely, FastAPI
needs to assign a name for each endpoint. Here is how you can provide such name:

```python
from openapi_to_fastapi.routes import RoutesMapping, RouteInfo
from openapi_to_fastapi.models import Operation

route_info = RouteInfo(
    factory=create_pet,
    name="Create a pet",
    response_description="A Pet",
    tags=["pets"],
)

# Or you can set the dynamic name based on API path and Operation structure
def name_factory(path: str, operation: Operation, **kwargs):
    return path.replace("/", " ")

route_info = RouteInfo(
    factory=proxy_route,
    name=name_factory,
)

```

## OpenAPI validation

This package also provides a CLI entrypoint to validate OpenAPI specs. It's especially useful when you need to define
you own set of rules for validation.

Imagine your API specs are stored in the separate repository and maintained by another team.
You also expect that all OpenAPI specs have only one endpoint defined (some internal agreement).

Now you can set up a CI check and validate them on every push.

Firstly create a file with a custom validator:

```python
# my_validator.py

from openapi_to_fastapi.validator import BaseValidator, OpenApiValidationError

class CustomError(OpenApiValidationError):
    pass

# important: must be inherited from BaseValidator
class MyValidator(BaseValidator):

    # implement this single method
    def validate_spec(self, spec: dict):
        if len(spec["paths"]) != 1:
            raise CustomError("Only one endpoint allowed")
```

Then run the tool:

```
openapi-validator --path ./standards -m my_validator.py -v MyValidator

===============================================================================
OpenAPI specs root path: ./standards
Validators: DefaultValidator, MyValidator
===============================================================================
File: ./standards/Current.json
[PASSED]
-------------------------------------------------------------------------------
File: ./standards/Metric.json
[PASSED]
-------------------------------------------------------------------------------
File: ./standards/BasicInfo.json
[PASSED]
-------------------------------------------------------------------------------
===============================================================================
Summary:
Total : 3
Passed: 3
Failed: 0
===============================================================================
```

This validator can also be reused during routes generation:

```python
router = make_router_from_specs(specs, routes, validators=[MyValidator])
```
