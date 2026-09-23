import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def generated_files(root: Path) -> dict[str, bytes]:
    paths = [
        *root.glob("schemas/*.schema.json"),
        *root.glob("src/generated/*.d.ts"),
        root / "src/index.ts",
    ]
    return {str(path.relative_to(root)): path.read_bytes() for path in paths if path.is_file()}


def main() -> int:
    with TemporaryDirectory(prefix="datapulse-contracts-") as temporary:
        generated = Path(temporary)
        run(sys.executable, "tools/export_schemas.py", "--output-dir", str(generated / "schemas"))
        run(
            "node", "tools/generate_types.mjs",
            "--schema-dir", str(generated / "schemas"),
            "--output-dir", str(generated / "src"),
        )
        expected = generated_files(generated)
        actual = generated_files(ROOT / "packages/schema")
        differences = sorted(
            name for name in expected.keys() | actual.keys()
            if expected.get(name) != actual.get(name)
        )
        if differences:
            print("Generated contracts are out of date:")
            for name in differences:
                print(f"  packages/schema/{name}")
            return 1
    print("Generated contracts match the current source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
