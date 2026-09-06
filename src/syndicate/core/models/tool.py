"""Tool abstraction interface for Syndicate."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from .task import ToolInputSchema


class Tool(ABC):
    """
    Abstract base class for all tools.

    Tools provide deterministic functionality for executing operations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the tool does."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> ToolInputSchema:
        """Return the input schema for this tool."""
        pass

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the provided input.

        Args:
            input_data: Dictionary containing input parameters.

        Returns:
            Dictionary containing tool output and status.
        """
        pass
