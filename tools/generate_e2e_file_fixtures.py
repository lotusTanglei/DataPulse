
import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
from tools.prepare_e2e import REPOSITORY_ROOT

FIXTURE_DIR = REPOSITORY_ROOT / "apps" / "web" / "e2e" / "fixtures"


def generate() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    workbook = openpyxl.Workbook()
    summary = workbook.active
    summary.title = "汇总"
    summary.append(["region", "amount"])
    summary.append(["华东", 120])
    summary.append(["华南", 98])
    detail = workbook.create_sheet("明细")
    detail.append(["order_id", "amount"])
    detail.append(["订单-001", 60])
    detail.append(["订单-002", 38])
    workbook.save(FIXTURE_DIR / "file-dataset.xlsx")

    table = pa.table(
        {
            "region": pa.array(["华东", "华南"]),
            "amount": pa.array([120.5, 98.0], type=pa.float64()),
        }
    )
    pq.write_table(table, FIXTURE_DIR / "file-dataset.parquet")


if __name__ == "__main__":
    generate()
