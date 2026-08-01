
from datetime import datetime
from io import BytesIO
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
from openpyxl.writer.excel import ExcelWriter
from tools.prepare_e2e import REPOSITORY_ROOT

FIXTURE_DIR = REPOSITORY_ROOT / "apps" / "web" / "e2e" / "fixtures"
FIXTURE_TIMESTAMP = datetime(2000, 1, 1)
ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


def _reproducible_workbook_bytes(workbook: openpyxl.Workbook) -> bytes:
    raw = BytesIO()
    ExcelWriter(workbook, ZipFile(raw, "w")).save()
    raw.seek(0)

    normalized = BytesIO()
    with ZipFile(raw) as source, ZipFile(normalized, "w") as target:
        for source_info in source.infolist():
            target_info = ZipInfo(source_info.filename, ZIP_TIMESTAMP)
            target_info.compress_type = ZIP_STORED
            target_info.create_system = 0
            target.writestr(target_info, source.read(source_info.filename))
    return normalized.getvalue()


def generate() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    workbook = openpyxl.Workbook()
    workbook.properties.created = FIXTURE_TIMESTAMP
    workbook.properties.modified = FIXTURE_TIMESTAMP
    summary = workbook.active
    summary.title = "汇总"
    summary.append(["region", "amount"])
    summary.append(["华东", 120])
    summary.append(["华南", 98])
    detail = workbook.create_sheet("明细")
    detail.append(["order_id", "amount"])
    detail.append(["订单-001", 60])
    detail.append(["订单-002", 38])
    (FIXTURE_DIR / "file-dataset.xlsx").write_bytes(
        _reproducible_workbook_bytes(workbook)
    )

    table = pa.table(
        {
            "region": pa.array(["华东", "华南"]),
            "amount": pa.array([120.5, 98.0], type=pa.float64()),
        }
    )
    pq.write_table(table, FIXTURE_DIR / "file-dataset.parquet")


if __name__ == "__main__":
    generate()
