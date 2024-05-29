import pydantic
import pytest
from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel
from starlette.status import HTTP_418_IM_A_TEAPOT

from openapi_to_fastapi.model_generator import load_models
from openapi_to_fastapi.routes import SpecRouter

# values aligned with the response defined in the data/definitions/CompanyBasicInfo.json
company_basic_info_resp = {
    "name": "Company",
    "companyId": "test",
    "companyForm": "Form",
    "registrationDate": "Long ago",
}


def test_routes_are_created(definitions_client, specs_root):
    assert definitions_client.post("/Company/BasicInfo").status_code != 404
    assert definitions_client.post("/Non/Existing/Stuff").status_code == 404

    assert definitions_client.get("/Company/BasicInfo").status_code == 405
    assert definitions_client.get("/Non/Existing/Stuff").status_code == 404


def test_pydantic_model_loading(specs_root):
    path = specs_root / "definitions" / "CompanyBasicInfo.json"
    raw_spec = path.read_text(encoding="utf8")
    module = load_models(raw_spec, "/Company/BasicInfo")
    assert module.BasicCompanyInfoRequest
    assert module.BasicCompanyInfoResponse
    assert module.HTTPValidationError
    assert module.ValidationError

    with pytest.raises(pydantic.ValidationError):
        module.BasicCompanyInfoRequest()

    with pytest.raises(pydantic.ValidationError):
        module.BasicCompanyInfoRequest(companyId=[])

    company_info_req = module.BasicCompanyInfoRequest(companyId="abc")
    assert company_info_req.model_dump() == {"companyId": "abc"}

    assert module.ValidationError(loc=[], msg="Crap", type="Error")


def test_weather_route_payload_errors(app, specs_root, client, json_snapshot):
    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post("/Weather/Current/Metric")
    def weather_metric(request):
        return {}

    app.include_router(spec_router.to_fastapi_router())

    resp = client.post("/Weather/Current/Metric", json={})
    assert resp.status_code == 422
    assert json_snapshot == resp.json(), "Missing payload"

    resp = client.post("/Weather/Current/Metric", json={"lat": "1,1.2", "lon": "99999"})
    assert resp.status_code == 422
    assert json_snapshot == resp.json(), "Incorrect payload type"


def test_company_custom_post_route(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post("/Company/BasicInfo")
    def weather_metric(request):
        return company_basic_info_resp

    app.include_router(spec_router.to_fastapi_router())

    resp = client.post("/Company/BasicInfo", json={"companyId": "test"})
    assert resp.status_code == 200, resp.json()
    assert resp.json() == company_basic_info_resp


def test_default_post_handler(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post()
    def company_info(request):
        return company_basic_info_resp

    app.include_router(spec_router.to_fastapi_router())
    resp = client.post("/Company/BasicInfo", json={"companyId": "test"})
    assert resp.status_code == 200
    assert resp.json() == company_basic_info_resp


def test_custom_route_definitions(app, client, specs_root, json_snapshot):
    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post("/Weather/Current/Metric")
    def weather_metric(request, vendor: str, auth_header: str = Header(...)):
        return {"customRoute": ""}

    app.include_router(spec_router.to_fastapi_router())
    resp = client.post("/Weather/Current/Metric", json={"lat": "30.5", "lon": 1.56})
    assert resp.status_code == 422
    assert json_snapshot == resp.json(), "Custom route definition"


def test_response_model_is_parsed(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post("/Weather/Current/Metric")
    def weather_metric(request):
        return {}

    spec_router.to_fastapi_router()
    assert spec_router.get_response_model("/Weather/Current/Metric", "get") is None
    resp_model = spec_router.get_response_model("/Weather/Current/Metric", "post")

    assert resp_model is not None
    with pytest.raises(pydantic.ValidationError):
        resp_model()

    assert resp_model(
        humidity=1, pressure=1, rain=False, temp=30, windSpeed=1, windDirection=1.0
    )


def test_routes_meta_info(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post(
        "/Weather/Current/Metric",
        name="The Route",
        tags=["Routes"],
        description="Route description",
        response_description="Response description",
    )
    def weather_metric(request):
        return {}

    router = spec_router.to_fastapi_router()
    route = [r for r in router.routes if r.path == "/Weather/Current/Metric"][0]
    assert route.name == "The Route"
    assert route.tags == ["Routes"]
    assert route.description == "Route description"
    assert route.response_description == "Response description"
    assert route.summary == "Current weather in a given location"

    # test that generating OpenAPI still works
    app.include_router(router)
    assert app.openapi()


def test_routes_meta_info_custom_name(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    def name_factory(path="", **kwargs):
        return path[1:]

    @spec_router.post("/Company/BasicInfo", name_factory=name_factory)
    def weather_metric(request):
        return {}

    router = spec_router.to_fastapi_router()
    route = [r for r in router.routes if r.path == "/Company/BasicInfo"][0]

    assert route.name == "Company/BasicInfo"
    assert route.summary == "Company/BasicInfo Data Product"
    # description by default is coming from spec
    assert route.description == "Information about the company"

    # test that generating OpenAPI still works
    app.include_router(router)
    assert app.openapi()


def test_custom_route_name_for_default_post(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    def name_factory(path="", **kwargs):
        return path[1:]

    @spec_router.post(name_factory=name_factory)
    def weather_metric(request):
        return {}

    router = spec_router.to_fastapi_router()
    route = [r for r in router.routes if r.path == "/Company/BasicInfo"][0]
    assert route.name == "Company/BasicInfo"
    assert route.description == "Information about the company"
    assert route.summary == "Company/BasicInfo Data Product"

    # test that generating OpenAPI still works
    app.include_router(router)
    assert app.openapi()


def test_headers_in_route_info_post(app, client, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    post_map = spec_router.post_map
    company_basic_info_headers = post_map["/Company/BasicInfo"].headers
    assert "authorization" in company_basic_info_headers
    assert "x-authorization-provider" in company_basic_info_headers

    weather_headers = post_map["/Weather/Current/Metric"].headers
    assert "authorization" in weather_headers
    assert "x-authorization-provider" in weather_headers
    assert "x-consent-token" in weather_headers


def test_deprecated(app, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    router = spec_router.to_fastapi_router()
    app.include_router(router)

    spec = app.openapi()
    assert spec["paths"]["/draft/Appliances/CoffeeBrewer"]["post"]["deprecated"] is True


def test_tags(app, specs_root):
    spec_router = SpecRouter(specs_root / "definitions")

    router = spec_router.to_fastapi_router()
    app.include_router(router)

    spec = app.openapi()
    assert spec["paths"]["/draft/Appliances/CoffeeBrewer"]["post"]["tags"] == ["Coffee"]


def test_custom_responses(app, specs_root):
    brew_spec = "/draft/Appliances/CoffeeBrewer"
    spec_router = SpecRouter(specs_root / "definitions")

    router = spec_router.to_fastapi_router()
    app.include_router(router)

    # Check custom response models are parsed
    route_info = spec_router.get_route_info(brew_spec, "post")
    resp_models = route_info.get_additional_response_models()
    assert issubclass(resp_models[418], BaseModel)

    # Check the response is added to OpenAPI spec and has a description and schema
    spec = app.openapi()
    responses = spec["paths"][brew_spec]["post"]["responses"]
    assert responses["418"]["description"] == "I'm a teapot"
    assert "$ref" in responses["418"]["content"]["application/json"]["schema"]

    # Check internals of the route and the parsed model
    route = [r for r in router.routes if r.path == brew_spec][0]
    assert route.responses[418]["description"] == "I'm a teapot"
    model = route.responses[418]["model"]
    assert issubclass(model, BaseModel)
    assert "ok" in model.model_fields
    assert "errorMessage" in model.model_fields


def test_dependencies(app, client, specs_root):
    async def teapot_dependency(request: Request):
        """
        Dependency used just for testing.
        """
        if request.headers.get("X-Brew") != "tea":
            raise HTTPException(
                HTTP_418_IM_A_TEAPOT,
                "I'm a teapot",
            )

    spec_router = SpecRouter(specs_root / "definitions")

    @spec_router.post("/Company/BasicInfo", dependencies=[Depends(teapot_dependency)])
    def weather_metric(request):
        return company_basic_info_resp

    app.include_router(spec_router.to_fastapi_router())

    # Normal request, not affected by the dependency
    resp = client.post(
        "/Company/BasicInfo", json={"companyId": "test"}, headers={"X-Brew": "tea"}
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json() == company_basic_info_resp

    # Custom request, affected by the dependency
    resp = client.post(
        "/Company/BasicInfo", json={"companyId": "test"}, headers={"X-Brew": "coffee"}
    )
    assert resp.status_code == 418, resp.json()
