import json
from pathlib import Path

from datapulse.contracts import CONTRACT_MODELS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "packages" / "schema" / "schemas"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for old_file in OUTPUT.glob("*.schema.json"):
        old_file.unlink()
    for name, model in sorted(CONTRACT_MODELS.items()):
        schema = model.model_json_schema(mode="validation")
        schema["$id"] = f"https://datapulse.dev/schemas/v1/{name}.schema.json"
        content = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (OUTPUT / f"{name}.schema.json").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
