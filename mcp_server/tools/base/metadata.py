"""Tool metadata and data classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolMetadata:
    """Metadata for a tool.

    Attributes:
        name: Unique tool identifier.
        description: Human-readable description of what the tool does.
        input_schema: JSON Schema for tool input parameters.
        output_schema: JSON Schema for tool output (optional).
        annotations: Optional tool annotations for MCP.
        tags: Optional list of tags for categorization.
        version: Tool version string.
        author: Tool author.
        enabled: Whether tool is enabled for execution.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "ToolBridge"
    enabled: bool = True

    def to_mcp_tool(self) -> dict[str, Any]:
        """Convert to MCP tool format for tools/list endpoint.

        Returns:
            Dictionary matching MCP Tool schema.
        """
        tool = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self.output_schema:
            tool["outputSchema"] = self.output_schema
        if self.annotations:
            tool["annotations"] = self.annotations
        return tool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "annotations": self.annotations,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "enabled": self.enabled,
        }


@dataclass
class RegisteredTool:
    """Internal representation of a registered tool."""

    tool: "BaseTool"  # Forward reference to avoid circular import
    metadata: ToolMetadata
    enabled: bool = True