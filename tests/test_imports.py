"""Package import smoke tests."""

from strands import Agent

import asset_shepherd


def test_package_and_strands_agent_are_importable() -> None:
    """Importing the package and Agent class does not instantiate an agent."""
    assert asset_shepherd.__name__ == "asset_shepherd"
    assert Agent.__name__ == "Agent"
