from collections.abc import Callable
from uuid import uuid4

from datapulse.contracts.dashboard import DashboardDocument
from datapulse.contracts.digital_human import DigitalHumanBinding
from datapulse.screen.access import ScreenAccessPolicy
from datapulse.screen.models import (
    ScreenCreate,
    ScreenDraftUpdate,
    ScreenResponse,
    ScreenSummary,
)
from datapulse.screen.repository import ScreenRepository


def _empty_document() -> DashboardDocument:
    return DashboardDocument(canvas={"width": 1920, "height": 1080})


class ScreenService:
    def __init__(
        self,
        *,
        repository: ScreenRepository,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory or (lambda: str(uuid4()))

    async def create(self, data: ScreenCreate) -> ScreenResponse:
        return await self._repository.create(
            data.name,
            data.draft_document or _empty_document(),
            description=data.description,
            screen_id=self._id_factory(),
        )

    async def list(self) -> tuple[ScreenSummary, ...]:
        screens = await self._repository.list()
        return tuple(
            ScreenSummary.model_validate(
                screen.model_dump(exclude={"draft_document", "published_document", "access_policy"})
            )
            for screen in screens
        )

    async def get(self, screen_id: str) -> ScreenResponse:
        return await self._repository.get(screen_id)

    async def save_draft(
        self,
        screen_id: str,
        data: ScreenDraftUpdate,
    ) -> ScreenResponse:
        if data.draft_document is not None:
            if data.expected_revision is None:
                raise ValueError("expected_revision is required when saving a draft.")
            return await self._repository.save_draft(
                screen_id,
                document=data.draft_document,
                expected_revision=data.expected_revision,
                name=data.name,
                description=data.description,
                access_policy=data.access_policy,
            )
        return await self._repository.update_metadata(
            screen_id,
            name=data.name,
            description=data.description,
            access_policy=data.access_policy,
        )

    async def update_access_policy(
        self,
        screen_id: str,
        access_policy: ScreenAccessPolicy,
    ) -> ScreenResponse:
        return await self._repository.update_access_policy(
            screen_id,
            access_policy=access_policy,
        )

    async def copy(self, screen_id: str) -> ScreenResponse:
        source = await self._repository.get(screen_id)
        copied_screen_id = self._id_factory()
        existing_names = {screen.name for screen in await self._repository.list()}
        base_name = f"{source.name} 副本"
        copy_name = base_name
        suffix = 2
        while copy_name in existing_names:
            copy_name = f"{base_name} {suffix}"
            suffix += 1
        component_ids = {
            component.id: self._id_factory()
            for component in source.draft_document.components
        }
        copied_components = []
        for component in source.draft_document.components:
            data_binding = component.data_binding
            if (
                component.type == "builtin.digital_human"
                and data_binding.get("source") == "components"
            ):
                binding = DigitalHumanBinding.model_validate(data_binding)
                data_binding = binding.model_copy(
                    update={
                        "variables": tuple(
                            variable.model_copy(
                                update={
                                    "component_id": component_ids.get(
                                        variable.component_id,
                                        variable.component_id,
                                    ),
                                },
                            )
                            for variable in binding.variables
                        ),
                    },
                ).model_dump(mode="json")
            copied_components.append(
                component.model_copy(
                    update={
                        "id": component_ids[component.id],
                        "data_binding": data_binding,
                    },
                    deep=True,
                )
            )
        components = tuple(copied_components)
        document = source.draft_document.model_copy(
            update={"components": components},
            deep=True,
        )
        return await self._repository.create(
            copy_name,
            document,
            description=source.description,
            screen_id=copied_screen_id,
        )

    async def delete(self, screen_id: str) -> None:
        await self._repository.delete(screen_id)
