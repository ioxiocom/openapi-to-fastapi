import json

import pydantic
import pytest
from fastapi import Header

from openapi_to_fastapi.model_generator import load_models
from openapi_to_fastapi.routes import RoutesMapping, make_router_from_specs


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


def test_weather_route_fetch(ihan_client):
    resp = ihan_client.post(
        "/Weather/Current/Metric", json={"lat": "30.5", "lon": 1.56}
    )
    assert resp.status_code == 200
    assert resp.json() == {}


def test_weather_route_custom_default_route(app, client, specs_root, snapshot):
    def make_post_route(model):
        def _route(request: model):
            return {"customDefault": ""}

        return _route

    routes = RoutesMapping(default_post=make_post_route)
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    resp = client.post("/Weather/Current/Metric", json={"lat": "30.5", "lon": 1.56})
    assert resp.status_code == 200
    assert resp.json() == {"customDefault": ""}


def test_weather_route_custom_route(app, client, specs_root, snapshot):
    def make_post_route(model):
        def _route(request: model):
            return {"customRoute": ""}

        return _route

    routes = RoutesMapping(post_map={"/Weather/Current/Metric": make_post_route})
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    resp = client.post("/Weather/Current/Metric", json={"lat": "30.5", "lon": 1.56})
    assert resp.status_code == 200
    assert resp.json() == {"customRoute": ""}


def test_custom_route_definitions(app, client, specs_root, snapshot):
    # Add required query param and a header
    def make_post_route(model):
        def _route(request: model, vendor: str, auth_header: str = Header(...)):
            return {"customRoute": ""}

        return _route

    routes = RoutesMapping(post_map={"/Weather/Current/Metric": make_post_route})
    app.include_router(make_router_from_specs(specs_root / "ihan", routes))
    resp = client.post("/Weather/Current/Metric", json={"lat": "30.5", "lon": 1.56})
    assert resp.status_code == 422
    snapshot.assert_match(resp.json(), "Custom route definition")
