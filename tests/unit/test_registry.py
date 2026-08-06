"""Unit tests for tool definitions, registration, and discovery."""

import pytest

from toolbridge.core.contracts import ToolDefinition, ToolInput, ToolOutput
from toolbridge.core.errors import DuplicateToolError, ToolNotFoundError
from toolbridge.core.registry import ToolRegistry


class EchoInput(ToolInput):
    """Test input contract."""

    text: str


class EchoOutput(ToolOutput):
    """Test output contract."""

    text: str


def echo(arguments: EchoInput) -> EchoOutput:
    """Return the provided test text."""

    return EchoOutput(text=arguments.text)


def definition(name: str = "echo") -> ToolDefinition:
    """Build a valid test definition."""

    return ToolDefinition(
        name=name,
        description=f"Run the {name} test tool.",
        input_model=EchoInput,
        output_model=EchoOutput,
        handler=echo,
        timeout_seconds=1.0,
    )


def test_registry_rejects_duplicate_names() -> None:
    registry = ToolRegistry()
    registry.register(definition())

    with pytest.raises(DuplicateToolError) as caught:
        registry.register(definition())

    assert caught.value.code.value == "duplicate_tool"
    assert caught.value.details == {"tool_name": "echo"}


def test_registry_discovers_tools_in_name_order() -> None:
    registry = ToolRegistry()
    registry.register(definition("zeta"))
    registry.register(definition("alpha"))

    discovered = registry.discover()

    assert [tool.name for tool in discovered] == ["alpha", "zeta"]
    assert discovered[0].input_schema["additionalProperties"] is False
    assert "text" in discovered[0].input_schema["properties"]
    assert "text" in discovered[0].output_schema["properties"]


def test_registry_reports_unknown_tool_safely() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolNotFoundError) as caught:
        registry.get("missing")

    assert caught.value.message == "The requested tool is not available."
    assert caught.value.details == {"tool_name": "missing"}


@pytest.mark.parametrize("name", ["", "UPPER", "has-hyphen", "1starts_with_number"])
def test_definition_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError):
        definition(name)
