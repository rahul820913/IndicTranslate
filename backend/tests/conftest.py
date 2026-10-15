import os
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["TRANSLATOR_BACKEND"] = "mock"
os.environ.pop("REDIS_URL", None)
pathlib.Path("test.db").unlink(missing_ok=True)

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def signup(client, email):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
