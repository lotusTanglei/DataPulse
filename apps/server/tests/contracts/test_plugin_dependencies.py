import pytest
from pydantic import ValidationError

from datapulse.contracts.dashboard import DashboardDocument


def test_published_document_preserves_exact_plugin_version():
    document = DashboardDocument.model_validate(
        {
            "canvas": {"width": 1920, "height": 1080},
            "plugin_dependencies": [{"id": "org.example.metric", "version": "1.2.3"}],
        }
    )
    assert document.model_dump()["plugin_dependencies"] == (
        {"id": "org.example.metric", "version": "1.2.3"},
    )


@pytest.mark.parametrize(
    "dependencies",
    [
        [{"id": "../escape", "version": "1.0.0"}],
        [{"id": "org.example.metric", "version": "latest"}],
        [
            {"id": "org.example.metric", "version": "1.0.0"},
            {"id": "org.example.metric", "version": "2.0.0"},
        ],
    ],
)
def test_dependency_rejects_unsafe_unpinned_or_conflicting_versions(dependencies):
    with pytest.raises(ValidationError):
        DashboardDocument.model_validate(
            {
                "canvas": {"width": 1920, "height": 1080},
                "plugin_dependencies": dependencies,
            }
        )
