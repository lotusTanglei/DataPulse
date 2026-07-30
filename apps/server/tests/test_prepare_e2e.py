import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PREPARE_PATH = Path(__file__).resolve().parents[3] / "tools" / "prepare_e2e.py"
SPEC = spec_from_file_location("prepare_e2e", PREPARE_PATH)
assert SPEC is not None and SPEC.loader is not None
PREPARE_E2E = module_from_spec(SPEC)
sys.modules[SPEC.name] = PREPARE_E2E
SPEC.loader.exec_module(PREPARE_E2E)
cleanup_run = PREPARE_E2E.cleanup_run
prepare = PREPARE_E2E.prepare


def test_parallel_preparations_keep_independent_runtime_state(tmp_path: Path) -> None:
    first_config = prepare(tmp_path)
    second_config = prepare(tmp_path)
    try:
        first = json.loads(first_config.read_text(encoding="utf-8"))
        second = json.loads(second_config.read_text(encoding="utf-8"))

        assert first_config != second_config
        assert Path(first["dataDir"]).exists()
        assert Path(second["dataDir"]).exists()
        assert first["dataDir"] != second["dataDir"]
        assert first["backendPort"] != first["frontendPort"]
        assert second["backendPort"] != second["frontendPort"]

        cleanup_run(first_config, tmp_path)

        assert not first_config.exists()
        assert not Path(first["dataDir"]).exists()
        assert second_config.exists()
        assert Path(second["dataDir"]).exists()
    finally:
        cleanup_run(first_config, tmp_path)
        cleanup_run(second_config, tmp_path)
