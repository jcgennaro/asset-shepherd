"""Strands model decorator: admission happens for every request, including retries."""

# Strands' abstract provider interface intentionally accepts arbitrary provider options.
# ruff: noqa: ANN401

from collections.abc import AsyncGenerator
from typing import Any, TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent

from asset_shepherd.spending import SpendLedger

T = TypeVar("T", bound=BaseModel)


class SpendingModel(Model):
    """Preserve provider state while bounding each inference against the site-wide ledger."""

    def __init__(self, model: Model, ledger: SpendLedger, provider: str, model_id: str) -> None:
        """Bind the immutable model configuration selected by the deployment."""
        self.model, self.ledger, self.provider, self.model_id = model, ledger, provider, model_id

    @property
    def stateful(self) -> bool:
        """Preserve Responses conversation-state semantics."""
        return self.model.stateful

    def get_config(self) -> Any:
        """Delegate configuration inspection without exposing ledger clients."""
        return self.model.get_config()

    def update_config(self, **model_config: Any) -> None:
        """Do not permit an output/tier override to invalidate the reserved envelope."""
        raise ValueError("Budgeted model configuration is immutable")

    async def stream(
        self, messages: Messages, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[StreamEvent, None]:
        """Reserve before inference, including failures without usage metadata."""
        reservation = self.ledger.reserve(self.provider, self.model_id)
        usage: object = None
        try:
            async for event in self.model.stream(messages, *args, **kwargs):
                metadata = event.get("metadata")
                if metadata is not None:
                    usage = metadata.get("usage")
                yield event
        finally:
            reservation.finish(usage)

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Reject the unmetered alternate path; the product uses streamed tool schemas."""
        raise ValueError("Use the metered model stream for structured tool output")
        yield {}  # pragma: no cover
