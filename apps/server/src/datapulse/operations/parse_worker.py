"""Internal worker entrypoint; decode untrusted input only after OS limits apply."""

import base64
import json
import sys
from pathlib import Path


def main() -> None:
    request = json.loads(Path(sys.argv[1]).read_text())
    path = Path(request["path"])
    try:
        if request["operation"] == "image":
            from datapulse.screen.media import MediaInspector, MediaLimits

            result = MediaInspector(MediaLimits(max_pixels=request["max_pixels"]))._image(
                path.read_bytes(), request["mime_type"]
            )
            payload = {
                "metadata": result.metadata.model_dump(mode="json"),
                "thumbnail": base64.b64encode(result.thumbnail or b"").decode(),
            }
        else:
            from datapulse.contracts.dataset import FileFormat
            from datapulse.filedata.parsers import _excel_sheet_names_sync, _parse_sync

            if request["operation"] == "sheets":
                payload = {"sheet_names": _excel_sheet_names_sync(path)}
            else:
                result = _parse_sync(
                    path,
                    FileFormat(request["format"]),
                    sheet_name=request["sheet_name"],
                    max_rows=request["max_rows"],
                )
                payload = {"parsed": result.model_dump(mode="json")}
        print(json.dumps({"ok": True, **payload}, allow_nan=False))
    except Exception as error:
        # Decoder tracebacks may contain input bytes or filesystem paths.
        code = (
            "IMAGE_PIXEL_LIMIT"
            if str(error) == "The image exceeds the pixel limit."
            else "INPUT_INVALID"
        )
        print(json.dumps({"ok": False, "error_code": code}))


if __name__ == "__main__":
    main()
