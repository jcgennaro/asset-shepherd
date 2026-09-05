"""Bound repeated deterministic sensing failures without making repair decisions."""

from strands.hooks import AfterToolsEvent, HookRegistry


class VisualSensingFailureGuard:
    """Allow one retry of a visual failure, then stop before another paid model call."""

    def __init__(self) -> None:
        """Initialize invocation-local failure counters."""
        self.reset()

    def reset(self) -> None:
        """Start a new explicitly invoked turn with one permitted retry."""
        self.failures: dict[str, int] = {}
        self.stop_error: str | None = None

    def register_hooks(self, registry: HookRegistry, **kwargs: object) -> None:
        """Stop only after the SDK records the complete tool-result batch."""
        registry.add_callback(AfterToolsEvent, self.after_tools)

    def after_tools(self, event: AfterToolsEvent) -> None:
        """Bound identical visual prerequisite failures across tool names."""
        for block in event.message["content"]:
            result = block.get("toolResult")
            if result is None or result.get("status") != "error":
                continue
            for content in result["content"]:
                text = content.get("text", "")
                marker = "Standardized visual sensing "
                if marker not in text:
                    continue
                # Count the same failed prerequisite across render and plan tools.
                error = text[text.index(marker) :].strip()[:500]
                self.failures[error] = self.failures.get(error, 0) + 1
                if self.failures[error] >= 2:
                    self.stop_error = f"Repeated visual sensing failure: {error}"
                    event.end_turn = "Visual evidence failed repeatedly; the workflow is stopped."
