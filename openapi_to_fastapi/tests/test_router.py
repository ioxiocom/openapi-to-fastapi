import json
from typing import Callable, Optional

import pydantic
import pytest
from fastapi import Header

from openapi_to_fastapi.model_generator import load_models
from openapi_to_fastapi.routes import RouteInfo, RoutesMapping, make_router_from_specs

# values aligned with the response defined in the data/ihan/CompanyBasicInfo.json
company_basic_info_resp = {
    "name": "Company",
    "companyId": "test",
    "companyForm": "Form",
    "registrationDate": "Long ago",
}


def test_routes_are_created(ihan_client, specs_root):
    assert ihan_client.post("/Company/BasicInfo").status_code != 404
    assert ihan_client.post("/Non/Existing/Stuff").status_code == 404

    assert ihan_client.get("/Company/BasicInfo").status_code == 405
    assert ihan_client.get("/Non/Existing/Stuff").status_code == 404


def test_pydantic_model_loading(specs_root):
    path = specs_root / "ihan" / "CompanyBasicInfo.json"
    spec = json.loads(path.read_text())
    module = load_models(spec, "/Company/BasicInfo")
    assert module.BasicCompanyInfoRequest
    assert module.BasicCompanyInfoResponse
    assert module.HTTPValidationError
    assert module.ValidationError

    with pytest.raises(pydantic.ValidationError):
        module.BasicCompanyInfoRequest()

    with pytest.raises(pydantic.ValidationError):
        module.BasicCompanyInfoRequest(companyId=[])

    company_info_req = module.BasicCompanyInfoRequest(companyId="abc")
    assert company_info_req.dict() == {"companyId": "abc"}

    assert module.ValidationError(loc=[], msg="Crap", type="Error")


def test_weather_route_payload_errors(ihan_client, snapshot):
    resp = ihan_client.post("/Weather/Current/Metric", json={})
    assert resp.status_code == 422
    snapshot.assert_match(resp.json(), "Missing payload")

    resp = ihan_client.post(
        "/Weather/Current/Metric", json={"lat": "1,1.2", "lon": "99999"}
    )
    assert resp.status_code == 422
    snapshot.assert_match(resp.json(), "Incorrect payload type")


def test_company_custom_post_route(app, client, specs_root, snapshot):
    def make_post_route(req_model, resp_model):
        def _route(request: req_model):
            return company_basic_info_resp

        return _route

    routes = RoutesMapping(default_post=RouteInfo(factory=make_post_route))
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    resp = client.post("/Company/BasicInfo", json={"companyId": "test"})
    assert resp.status_code == 200, resp.json()
    assert resp.json() == company_basic_info_resp


def test_weather_route_custom_route(app, client, specs_root, snapshot):
    def make_post_route(req_model, resp_model):
        def _route(request: req_model):
            return company_basic_info_resp

        return _route

    routes = RoutesMapping(
        post_map={"/Company/BasicInfo": RouteInfo(factory=make_post_route)}
    )
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    resp = client.post("/Company/BasicInfo", json={"companyId": "test"})
    assert resp.status_code == 200
    assert resp.json() == company_basic_info_resp


def test_custom_route_definitions(app, client, specs_root, snapshot):
    # Add required query param and a header
    def make_post_route(model, *args):
        def _route(request: model, vendor: str, auth_header: str = Header(...)):
            return {"customRoute": ""}

        return _route

    routes = RoutesMapping(
        post_map={"/Weather/Current/Metric": RouteInfo(factory=make_post_route)}
    )
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    resp = client.post("/Weather/Current/Metric", json={"lat": "30.5", "lon": 1.56})
    assert resp.status_code == 422
    snapshot.assert_match(resp.json(), "Custom route definition")


def test_response_model_is_parsed(app, client, specs_root):
    resp_model: Optional[Callable] = None

    def make_post_route(req_model, _resp_model):
        nonlocal resp_model
        resp_model = _resp_model
        return lambda request: {}

    routes = RoutesMapping(default_post=RouteInfo(factory=make_post_route))
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    assert resp_model is not None
    with pytest.raises(pydantic.ValidationError):
        resp_model()


def test_routes_meta_info(app, client, specs_root):
    def make_post_route(req_model, resp_model):
        def _route(request: req_model):
            return {}

        return _route

    routes = RoutesMapping(
        default_post=RouteInfo(
            factory=make_post_route,
            name="The Route",
            tags=["Routes"],
            description="Route description",
            response_description="Response description",
        )
    )
    router = make_router_from_specs(specs_root / "ihan", routes)
    route = router.routes[0]
    assert route.name == "The Route"
    assert route.tags == ["Routes"]
    assert route.description == "Route description"
    assert route.response_description == "Response description"


def test_routes_meta_info_custom_name(app, client, specs_root):
    def make_post_route(req_model, resp_model):
        def _route(request: req_model):
            return {}

        return _route

    def name_factory(path="", **kwargs):
        return path[1:]

    routes = RoutesMapping(
        default_post=RouteInfo(factory=make_post_route, name_factory=name_factory,)
    )
    router = make_router_from_specs(specs_root / "ihan", routes)
    route = router.routes[0]

    assert route.name == "Company/BasicInfo"
    # description by default is coming from spec
    assert route.description == "Information about the company"
