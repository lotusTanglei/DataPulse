import csv
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def test_four_industry_scenario_packs_reference_committed_sample_data() -> None:
    manifest_path = REPOSITORY_ROOT / "fixtures" / "scenarios" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert {pack["id"] for pack in manifest["packs"]} == {
        "business",
        "operations",
        "sales",
        "equipment",
    }
    for pack in manifest["packs"]:
        sample_path = REPOSITORY_ROOT / pack["sample_data"]
        assert sample_path.is_file()
        with sample_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) >= 3
        assert set(pack["field_mapping"].values()) <= set(rows[0])
