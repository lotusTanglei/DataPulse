from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest

from tests.support.app import AppClient, build_test_app


@pytest.fixture
def file_app(tmp_path: Path) -> Iterator[AppClient]:
    with build_test_app(tmp_path) as app_client:
        yield app_client


def setup_admin(app_client: AppClient) -> None:
    response = app_client.client.post(
        "/api/auth/setup",
        json={
            "code": app_client.setup_code,
            "username": "admin",
            "password": "long-enough-password",
        },
        headers={"Origin": app_client.origin},
    )
    assert response.status_code == 201


def mutation_headers(app_client: AppClient) -> dict[str, str]:
    return {
        "Origin": app_client.origin,
        "X-CSRF-Token": app_client.client.cookies["datapulse_csrf"],
    }


def excel_bytes() -> bytes:
    workbook = openpyxl.Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["metric", "value"])
    summary.append(["revenue", 100])
    detail = workbook.create_sheet("Detail")
    detail.append(["order_id", "amount"])
    detail.append(["A-1", 60])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_file_upload_create_dataset_preview_and_in_use_delete(file_app: AppClient) -> None:
    assert file_app.client.get("/api/admin/files").status_code == 401
    setup_admin(file_app)

    no_csrf = file_app.client.post(
        "/api/admin/files",
        files={"file": ("sales.csv", b"region,amount\nnorth,10\n", "text/csv")},
        headers={"Origin": file_app.origin},
    )
    assert no_csrf.status_code == 403

    uploaded = file_app.client.post(
        "/api/admin/files",
        files={"file": ("sales.csv", b"region,amount\nnorth,10\nsouth,20\n", "text/csv")},
        headers=mutation_headers(file_app),
    )
    assert uploaded.status_code == 201
    asset = uploaded.json()
    assert asset["format"] == "csv"
    assert asset["row_count"] == 2
    assert [field["name"] for field in asset["fields"]] == ["region", "amount"]

    listed = file_app.client.get("/api/admin/files")
    assert listed.status_code == 200
    assert listed.json() == [asset]

    created = file_app.client.post(
        "/api/admin/datasets/files",
        json={
            "name": "销售文件数据集",
            "file_asset_id": asset["id"],
            "max_rows": 5000,
            "timeout_seconds": 30,
        },
        headers=mutation_headers(file_app),
    )
    assert created.status_code == 201
    dataset = created.json()
    assert dataset["data_source_id"] is None
    assert dataset["definition"]["query"]["kind"] == "file"
    assert dataset["definition"]["query"]["asset_id"] == asset["id"]

    preview = file_app.client.post(
        f"/api/admin/datasets/{dataset['id']}/preview",
        json={"parameters": {}},
        headers=mutation_headers(file_app),
    )
    assert preview.status_code == 200
    assert preview.json()["rows"] == [["north", 10], ["south", 20]]

    in_use = file_app.client.delete(
        f"/api/admin/files/{asset['id']}",
        headers=mutation_headers(file_app),
    )
    assert in_use.status_code == 409
    assert in_use.json()["error"]["code"] == "FILE_IN_USE"


def test_file_api_rejects_missing_asset_and_preserves_sql_dataset_behavior(
    file_app: AppClient,
) -> None:
    setup_admin(file_app)

    missing = file_app.client.post(
        "/api/admin/datasets/files",
        json={
            "name": "缺失文件",
            "file_asset_id": "missing",
            "max_rows": 5000,
            "timeout_seconds": 30,
        },
        headers=mutation_headers(file_app),
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_file_preview_supports_csv_and_excel_sheets(file_app: AppClient) -> None:
    unauthenticated = file_app.client.get("/api/admin/files/missing/preview")
    assert unauthenticated.status_code == 401
    setup_admin(file_app)

    csv_upload = file_app.client.post(
        "/api/admin/files",
        files={"file": ("sales.csv", b"region,amount\nnorth,10\nsouth,20\n", "text/csv")},
        headers=mutation_headers(file_app),
    )
    assert csv_upload.status_code == 201
    csv_preview = file_app.client.get(
        f"/api/admin/files/{csv_upload.json()['id']}/preview",
        headers={"Origin": file_app.origin},
    )
    assert csv_preview.status_code == 200
    assert csv_preview.json()["sheet_names"] == []
    assert csv_preview.json()["selected_sheet"] is None
    assert csv_preview.json()["result"]["rows"] == [["north", 10], ["south", 20]]

    excel_upload = file_app.client.post(
        "/api/admin/files",
        files={
            "file": (
                "sales.xlsx",
                excel_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=mutation_headers(file_app),
    )
    assert excel_upload.status_code == 201
    asset_id = excel_upload.json()["id"]

    default_preview = file_app.client.get(f"/api/admin/files/{asset_id}/preview")
    assert default_preview.status_code == 200
    assert default_preview.json()["sheet_names"] == ["Summary", "Detail"]
    assert default_preview.json()["selected_sheet"] == "Summary"
    assert default_preview.json()["result"]["rows"] == [["revenue", 100]]

    detail_preview = file_app.client.get(
        f"/api/admin/files/{asset_id}/preview",
        params={"sheet_name": "Detail"},
    )
    assert detail_preview.status_code == 200
    assert detail_preview.json()["selected_sheet"] == "Detail"
    assert detail_preview.json()["result"]["rows"] == [["A-1", 60]]

    unknown_sheet = file_app.client.get(
        f"/api/admin/files/{asset_id}/preview",
        params={"sheet_name": "Missing"},
    )
    assert unknown_sheet.status_code == 422
    assert unknown_sheet.json()["error"]["code"] == "FILE_PARSE_INVALID"

    missing_asset = file_app.client.get("/api/admin/files/missing/preview")
    assert missing_asset.status_code == 404
    assert missing_asset.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_malformed_json_upload_returns_stable_error_and_cleans_storage(
    file_app: AppClient,
) -> None:
    setup_admin(file_app)

    response = file_app.client.post(
        "/api/admin/files",
        files={"file": ("broken.json", b"[{\"region\":", "application/json")},
        headers={**mutation_headers(file_app), "X-Request-ID": "bad-json-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_PARSE_INVALID"
    assert response.json()["error"]["request_id"] == "bad-json-1"
    assert response.headers["x-request-id"] == "bad-json-1"
    assert list((file_app.database_path.parent / "files").glob("*")) == []
    assert file_app.client.get("/api/admin/files").json() == []
