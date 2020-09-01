from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from openapi_to_fastapi.routes import RoutesMapping, make_router_from_specs


@pytest.fixture
def specs_root():
    return (Path(__file__).absolute().parent / "data").absolute()


@pytest.fixture
def app():
    return FastAPI()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def ihan_client(specs_root):
    app = FastAPI()
    app.include_router(make_router_from_specs(specs_root / "ihan", RoutesMapping()))
    return TestClient(app)
