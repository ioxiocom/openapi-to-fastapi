## Reasoning

[FastAPI](https://github.com/tiangolo/fastapi) is an awesome framework that simplifies
the process of creating APIs. One of the most exciting features is that it can generate
OpenAPI specs out of the box. But what if.. you have an OpenAPI spec and you need to
create an API from it?

One day we faced that problem — we had to create an API from multiple OpenAPI specs, and
make sure that the incoming requests and the outgoing responses were aligned with the
models defined the specs.

> ⚠️ This library was created to cover only our own needs first. So for now it's not
> suitable for everyone and has a lot of technical restrictions. Please consider it as
> experimental stuff

## Installation

The package is available on PyPi:

```bash
pip install openapi-to-fastapi
```

## Generating FastAPI routes

The main purpose of this library is to generate FastAPI routes from OpenAPI specs. This
is done by:

```python
from pathlib import Path
from openapi_to_fastapi.routes import SpecRouter

specs = Path("./specs")

router = SpecRouter(specs).to_fastapi_router()
```

The code above will create a FastAPI router that can be either included into the main
router, or used as the default one.

Imagine you have a following spec (some parts are cut off for brevity):

```json
{
  "openapi": "3.0.2",
  "paths": {
    "/Company/BasicInfo": {
      "post": {
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BasicCompanyInfoRequest",
                "responses": {
                  "200": {
                    "content": {
                      "application/json": {
                        "schema": {
                          "$ref": "#/components/schemas/BasicCompanyInfoResponse"
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
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
                "type": "string"
              },
              "companyId": {
                "title": "ID of the company",
                "type": "string"
              },
              "companyForm": {
                "title": "The company form of the company",
                "type": "string"
              }
            }
          }
        }
      }
    }
  }
}
```

The FastAPI route equivalent could look like this:

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

And `openapi-to-fastapi` can create it automagically.

### Custom routes

In most cases it makes no sense to create an API without any business logic.

Here's how to define it:

```python
from fastapi import Header, HTTPException
from openapi_to_fastapi.routes import SpecRouter

spec_router = SpecRouter("./specs")

# Default handler for all POST endpoints found in the spec
@spec_router.post()
def hello_world(params, x_my_token: str = Header(...)):
    if x_my_token != "my_token":
        raise HTTPException(status_code=403, detail="Sorry")
    return {"Hello": "World"}

# Specific endpoint for a "/pet" route
@spec_router.post("/pet")
def create_pet(params):
    pet = db.make_pet(name=params.name)
    return pet.to_dict()

router = spec_router.to_fastapi_router()
```

### API Documentation

Now after you have a lot of routes, you might want to leverage another great feature of
FastAPI — auto documentation.

Request and response models are already handled. But to display documentation nicely,
FastAPI needs to assign a name for each endpoint. Here is how you can provide such name:

```python
from openapi_to_fastapi.routes import SpecRouter

spec_router = SpecRouter("./specs")

@spec_router.post(
    "/pet",
    name="Create a pet",
    description="Create a pet",
    response_description="A Pet",
    tags=["pets"],
)
def create_pet(params):
    return {}

# Or you can set the dynamic name based on API path
def name_factory(path: str, **kwargs):
    return path.replace("/", " ")

@spec_router.post(name_factory=name_factory)
def create_pet(params):
    return {}

```

## OpenAPI validation

This package also provides a CLI entrypoint to validate OpenAPI specs. It's especially
useful when you need to define you own set of rules for validation.

Imagine your API specs are stored in a separate repository and maintained by another
team. You also expect that all OpenAPI specs have only one endpoint defined (some
internal agreement).

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

This validator can also be reused when generating routes:

```python
router = SpecRouter(specs, validators=[MyValidator])
```

## Development

You will need:

- Python 3.9+ (tested on 3.9 - 3.13)
- [pre-commit](https://pre-commit.com/#install)

Before working on the project, make sure you run:

```shell
pre-commit install
```

After making changes you can run tests:

```shell
poetry run invoke test
```

## License

This code is released under the BSD 3-Clause license. Details in the
[LICENSE](./LICENSE) file.
