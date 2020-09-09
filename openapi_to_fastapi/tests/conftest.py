from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from openapi_to_fastapi.routes import SpecRouter


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
    spec_router = SpecRouter(specs_root / "ihan")
    app.include_router(spec_router.to_fastapi_router())
    return TestClient(app)
