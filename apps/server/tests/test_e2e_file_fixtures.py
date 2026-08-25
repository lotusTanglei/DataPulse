from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools import generate_e2e_file_fixtures


def test_generate_produces_reproducible_binary_fixtures(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate_e2e_file_fixtures, "FIXTURE_DIR", tmp_path)

    generate_e2e_file_fixtures.generate()
    first_xlsx = (tmp_path / "file-dataset.xlsx").read_bytes()
    first_parquet = (tmp_path / "file-dataset.parquet").read_bytes()

    time.sleep(2.1)
    generate_e2e_file_fixtures.generate()

    assert (tmp_path / "file-dataset.xlsx").read_bytes() == first_xlsx
    assert (tmp_path / "file-dataset.parquet").read_bytes() == first_parquet
