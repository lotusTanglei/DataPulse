import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    run(sys.executable, "tools/export_schemas.py")
    run("node", "tools/generate_types.mjs")
    run("git", "diff", "--exit-code", "--", "packages/schema")
