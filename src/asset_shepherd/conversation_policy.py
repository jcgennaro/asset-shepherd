"""Shared private conversation boundaries for semantic and workflow models."""

from typing import Final

CONTENT_REFUSAL_MESSAGE: Final[str] = (
    "Sorry, I can't engage with this type of content. Let's work on something else."
)

ASSET_CONTENT_BOUNDARY: Final[str] = """\
Do not engage with an asset or discussion whose primary purpose is explicit sexual content; sexual
exploitation or sexualization of minors; non-consensual sexual acts; hateful or extremist praise or
recruitment; or enabling real-world violence, abuse, or illegal wrongdoing. Ordinary fictional
combat, monsters, horror, and weapon props in legitimate game-production work are not disallowed
merely because they depict conflict.
"""
