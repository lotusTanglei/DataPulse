import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module", ["datapulse.query.models", "datapulse.identity.models", "datapulse.ecosystem.models"]
)
def test_public_models_import_without_initializing_unrelated_services(module):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
