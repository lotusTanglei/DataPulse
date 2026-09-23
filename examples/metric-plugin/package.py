"""Package the previously built, self-contained example module (no ZIP directories)."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

root = Path(__file__).resolve().parent
output = root / "dist" / "org.datapulse.example.metrics-1.0.0.zip"
with ZipFile(output, "w", compression=ZIP_DEFLATED) as package:
    for name, path in [
        ("manifest.json", root / "manifest.json"),
        ("index.mjs", root / "dist" / "index.mjs"),
    ]:
        package.writestr(
            ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)),
            path.read_bytes(),
            compress_type=ZIP_DEFLATED,
        )
print(output)
