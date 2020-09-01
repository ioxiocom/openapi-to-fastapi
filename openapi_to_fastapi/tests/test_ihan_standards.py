import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import APIRouter

from ..routes import validate_spec_and_create_routes
from ..validator import ihan_standards as ihan

# Note: It's easier to get some 100% valid spec and corrupt it
# instead of having multiple incorrect specs in the repo

SPECS_ROOT_DIR = Path(__file__).absolute().parent / "data"
COMPANY_BASIC_INFO: dict = json.loads(
    (SPECS_ROOT_DIR / "ihan" / "CompanyBasicInfo.json").read_text()
)


_router = APIRouter()
validators = [ihan.IhanStandardsValidator]


def check_validation_error(tmp_path, spec: dict, exception):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    with pytest.raises(exception):
        validate_spec_and_create_routes(_router, spec_path, validators)


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_standards_has_non_post_method(method, tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    spec["paths"]["/Company/BasicInfo"][method] = {
        "description": "Method which should not exist"
    }
    check_validation_error(tmp_path, spec, ihan.OnlyPostMethodAllowed)


def test_post_method_is_missing(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    del spec["paths"]["/Company/BasicInfo"]["post"]
    check_validation_error(tmp_path, spec, ihan.PostMethodIsMissing)


def test_many_endpoints(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    spec["paths"]["/pets"] = {"post": {"description": "Pet store, why not?"}}
    check_validation_error(tmp_path, spec, ihan.OnlyOneEndpointAllowed)


def test_no_endpoints(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    del spec["paths"]
    check_validation_error(tmp_path, spec, ihan.NoEndpointsDefined)


def test_missing_field_body(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    del spec["paths"]["/Company/BasicInfo"]["post"]["requestBody"]
    check_validation_error(tmp_path, spec, ihan.RequestBodyMissing)


def test_missing_200_response(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    del spec["paths"]["/Company/BasicInfo"]["post"]["responses"]["200"]
    check_validation_error(tmp_path, spec, ihan.ResponseBodyMissing)


def test_wrong_content_type_of_request_body(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    request_body = spec["paths"]["/Company/BasicInfo"]["post"]["requestBody"]
    schema = deepcopy(request_body["content"]["application/json"])
    request_body["content"]["text/plan"] = schema
    del request_body["content"]["application/json"]
    check_validation_error(tmp_path, spec, ihan.WrongContentType)


def test_wrong_content_type_of_response(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    response = spec["paths"]["/Company/BasicInfo"]["post"]["responses"]["200"]
    schema = deepcopy(response["content"]["application/json"])
    response["content"]["text/plan"] = schema
    del response["content"]["application/json"]
    check_validation_error(tmp_path, spec, ihan.WrongContentType)


def test_component_schema_is_missing(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    del spec["components"]["schemas"]
    check_validation_error(tmp_path, spec, ihan.SchemaMissing)


@pytest.mark.parametrize(
    "model_name", ["BasicCompanyInfoRequest", "BasicCompanyInfoResponse"]
)
def test_component_is_missing(model_name, tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    del spec["components"]["schemas"][model_name]
    check_validation_error(tmp_path, spec, ihan.SchemaMissing)


def test_non_existing_component_defined_in_body(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    body = spec["paths"]["/Company/BasicInfo"]["post"]["requestBody"]
    body["content"]["application/json"]["schema"]["$ref"] += "blah"
    check_validation_error(tmp_path, spec, ihan.SchemaMissing)


def test_non_existing_component_defined_in_response(tmp_path):
    spec = deepcopy(COMPANY_BASIC_INFO)
    resp_200 = spec["paths"]["/Company/BasicInfo"]["post"]["responses"]["200"]
    resp_200["content"]["application/json"]["schema"]["$ref"] += "blah"
    check_validation_error(tmp_path, spec, ihan.SchemaMissing)
