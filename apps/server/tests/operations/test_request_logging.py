import json
import logging

from tests.support.app import build_test_app


def test_request_logs_use_route_templates_and_never_log_credentials(tmp_path, caplog, monkeypatch):
    with (
        build_test_app(tmp_path) as app,
        caplog.at_level(logging.INFO, logger="datapulse.requests"),
    ):
        monkeypatch.setattr(logging.getLogger("datapulse.requests"), "handlers", [caplog.handler])
        response = app.client.get(
            "/api/admin/screens/private-id?ticket=private-ticket",
            headers={
                "Authorization": "Bearer private-token",
                "Cookie": "private-cookie",
                "X-Request-ID": "fixture-request-001",
            },
        )
        assert response.status_code == 401
        app.client.get("/unknown/private-token?password=private-password")
    entries = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "datapulse.requests"
    ]
    assert len(entries) == 2
    assert entries[0]["route"] == "/api/admin/screens/{screen_id}"
    assert entries[0]["request_id"] == "fixture-request-001"
    assert entries[0]["status"] == 401
    assert entries[0]["duration_ms"] >= 0
    assert entries[1]["route"] == "unmatched"
    assert "private-" not in json.dumps(entries)
