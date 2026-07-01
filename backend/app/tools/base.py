"""Base tool interface for all research tools."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all tools in the research platform.

    Every tool must implement the `run` method with a unified interface:
    - Input: dict of parameters
    - Output: dict with at least `success` (bool) and `data` or `error` fields
    """

    name: str = "base_tool"
    description: str = "Base tool description"

    @abstractmethod
    async def run(self, input: dict) -> dict:
        """Execute the tool with the given input parameters.

        Args:
            input: Dictionary containing tool-specific parameters.

        Returns:
            dict with keys:
                - success (bool): Whether the execution succeeded
                - data (Any): The result data on success
                - error (str | None): Error message on failure
        """
        ...

    def to_dict(self) -> dict:
        """Return tool metadata as a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r})>"
