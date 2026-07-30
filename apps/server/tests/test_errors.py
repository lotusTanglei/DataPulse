from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from datapulse.errors import (
    DataPulseError,
    install_error_handlers,
    request_id_middleware,
)


def build_error_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)

    @app.get("/api/test-error")
    async def test_error() -> None:
        raise DataPulseError(
            code="TEST_INVALID",
            message="Invalid test input.",
            status_code=422,
        )

    class Payload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        name: str

    @app.post("/api/test-validation")
    async def test_validation(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    return app


def test_datapulse_error_uses_stable_envelope() -> None:
    response = TestClient(build_error_app()).get("/api/test-error")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "TEST_INVALID",
            "message": "Invalid test input.",
            "request_id": response.headers["x-request-id"],
            "field_errors": [],
        }
    }


def test_valid_caller_request_id_is_preserved() -> None:
    response = TestClient(build_error_app()).get(
        "/api/test-error",
        headers={"X-Request-ID": "request-123"},
    )

    assert response.headers["x-request-id"] == "request-123"
    assert response.json()["error"]["request_id"] == "request-123"


def test_invalid_or_oversized_request_id_is_replaced() -> None:
    client = TestClient(build_error_app())

    invalid = client.get("/api/test-error", headers={"X-Request-ID": "bad id!"})
    oversized = client.get("/api/test-error", headers={"X-Request-ID": "x" * 129})

    assert invalid.headers["x-request-id"] != "bad id!"
    assert oversized.headers["x-request-id"] != "x" * 129
    assert len(invalid.headers["x-request-id"]) == 36
    assert len(oversized.headers["x-request-id"]) == 36


def test_request_validation_uses_stable_error_envelope() -> None:
    response = TestClient(build_error_app()).post(
        "/api/test-validation",
        json={"unexpected": True},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert {item["field"] for item in response.json()["error"]["field_errors"]} == {
        "name",
        "unexpected",
    }
