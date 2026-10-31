from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredOutputGateway(Protocol):
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        model: str | None = None,
        timeout_seconds: int | float | None = None,
    ) -> T: ...


__all__ = ["StructuredOutputGateway"]
