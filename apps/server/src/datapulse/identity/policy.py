"""Explicit Studio route policy; unclassified management routes remain admin-only."""

from fastapi import Request

from datapulse.identity.service import forbidden
from datapulse.metadata import AdminAccount

# A route must be classified by its defining module AND endpoint name. New
# endpoints do not inherit privileges from URL-prefix or HTTP-method guessing.
_RESOURCE_ROUTES: dict[str, dict[str, tuple[str, str, str]]] = {
    "datapulse.datasource.api": {
        name: ("datasource", "datasource_id", permission)
        for permission, names in {
            "read": [
                "get_datasource",
                "list_namespaces",
                "list_relations",
                "describe_relation",
                "preview_relation",
                "query_datasource",
            ],
            "write": ["update_datasource", "delete_datasource", "test_datasource"],
        }.items()
        for name in names
    },
    "datapulse.dataset.api": {
        name: ("dataset", "dataset_id", permission)
        for permission, names in {
            "read": ["get_dataset", "preview_dataset", "get_dataset_profile"],
            "write": ["update_dataset", "delete_dataset", "update_dataset_profile"],
        }.items()
        for name in names
    },
    "datapulse.filedata.api": {
        "preview_file": ("file", "asset_id", "read"),
        "delete_file": ("file", "asset_id", "write"),
    },
    "datapulse.screen.api": {
        name: ("screen", "screen_id", permission)
        for permission, names in {
            "read": ["get_screen", "copy_screen"],
            "write": ["update_screen", "delete_screen"],
            "publish": ["publish_screen", "update_screen_access_policy"],
        }.items()
        for name in names
    },
    "datapulse.screen.runtime_api": {"query_draft_component": ("screen", "screen_id", "read")},
    "datapulse.display.api": {"generate_display_key": ("screen", "screen_id", "publish")},
    "datapulse.screen.asset_api": {
        name: ("asset", "asset_id", permission)
        for permission, names in {
            "read": [
                "asset_metadata",
                "asset_references",
                "asset_thumbnail",
                "asset_preview",
                "get_asset",
            ],
            "write": ["update_asset", "delete_asset", "replace_asset"],
        }.items()
        for name in names
    },
}
_LISTS = {
    "datapulse.datasource.api": {"list_datasources"},
    "datapulse.dataset.api": {"list_datasets"},
    "datapulse.filedata.api": {"list_files"},
    "datapulse.screen.api": {"list_screens"},
    "datapulse.screen.asset_api": {"list_assets", "expiring_assets", "asset_usage"},
}
_CREATES = {
    "datapulse.datasource.api": {"create_datasource", "test_datasource_config"},
    "datapulse.dataset.api": {"create_dataset", "create_file_dataset"},
    "datapulse.filedata.api": {"upload_file"},
    "datapulse.screen.api": {
        "create_screen",
        "compile_dashboard_plan",
        "recompile_dashboard_plan",
    },
    "datapulse.screen.asset_api": {"upload_asset"},
    "datapulse.ai.api": {"analyze", "chart", "screen", "edit_screen", "edit"},
}
_IDENTITY = {
    "identity_directory",
    "list_permissions",
    "set_permission",
    "revoke_permission",
    "resource_access",
}


async def authorize_request(request: Request, user: AdminAccount) -> None:
    if user.role == "admin" or not request.url.path.startswith("/api/admin/"):
        return
    service = request.app.state.identity_service
    endpoint = request.scope.get("endpoint")
    module = getattr(endpoint, "__module__", "")
    name = getattr(endpoint, "__name__", "")
    resource = _RESOURCE_ROUTES.get(module, {}).get(name)
    if resource:
        kind, parameter, permission = resource
        identifier = request.path_params[parameter]
        await service.require_access(user, kind, identifier, permission)
        if name == "copy_screen":
            service.require_creator(user)
        # Metadata includes binding IDs and fields; reads must respect revoked
        # dependencies just as the later cached query does.
        await service.check_stored_references(user, kind, identifier)
    elif name in _LISTS.get(module, set()):
        pass  # The endpoint filters its list using this same service.
    elif name in _CREATES.get(module, set()):
        service.require_creator(user)
    elif module == "datapulse.screen.runtime_api" and name == "query_document_component":
        pass  # All submitted bindings are authorized below.
    elif module == "datapulse.speech.api" and name in {
        "speech_provider_directory",
        "speech_provider_voices",
        "preview_plan",
        "queue_task",
        "get_task",
        "cancel_task",
    }:
        service.require_creator(user)
        if name == "speech_provider_voices":
            await service.require_speech_provider(user, request.path_params["provider_id"])
        elif name == "queue_task":
            if request.query_params.get("approved", "false").lower() == "true":
                raise forbidden()
            await service.require_speech_plan(user, plan_id=request.path_params["plan_id"])
        elif name in {"get_task", "cancel_task"}:
            await service.require_speech_plan(user, task_id=request.path_params["task_id"])
    elif module == "datapulse.ai.api" and name == "ai_status":
        pass
    elif module == "datapulse.ecosystem.api" and name in {
        "list_packages",
        "get_package",
        "plugin_file",
        "apply_template",
    }:
        if name == "apply_template":
            service.require_creator(user)
    elif module == "datapulse.identity.api" and name in _IDENTITY:
        pass  # Resource-owner checks live with the grants transaction.
    else:
        raise forbidden()
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type not in {"multipart/form-data", "application/x-www-form-urlencoded"}:
        body = await request.body()
        if not body:
            return
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError):
            return  # FastAPI reports invalid input through its normal validation handler.
        if module == "datapulse.datasource.api" and isinstance(payload, dict):
            config = payload.get("config")
            if isinstance(config, dict) and config.get("type") == "sqlite":
                # Server-local paths are not caller-owned resources. Registering
                # an alias or changing a shared source's path bypasses ID grants.
                # Editors can query/test the unchanged, explicitly shared source.
                raise forbidden()
        if (
            module == "datapulse.speech.api"
            and name == "preview_plan"
            and isinstance(payload, dict)
        ):
            await service.require_speech_scope(
                user,
                payload.get("screen_id", ""),
                payload.get("component_id", ""),
                payload.get("provider_id", ""),
            )
        if (
            module == "datapulse.datasource.api"
            and name == "test_datasource_config"
            and isinstance(payload, dict)
        ):
            datasource_id = payload.get("datasource_id")
            if isinstance(datasource_id, str) and datasource_id:
                # This endpoint can reuse stored credentials with an edited host.
                # A read grant must never authorize sending those secrets elsewhere.
                await service.require_access(user, "datasource", datasource_id, "write")
        if (
            name == "update_screen"
            and isinstance(payload, dict)
            and payload.get("access_policy") is not None
        ):
            await service.require_access(
                user, "screen", request.path_params["screen_id"], "publish"
            )
        await service.check_references(user, payload, file_context=(name == "create_file_dataset"))
