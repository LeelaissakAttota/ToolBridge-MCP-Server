"""Tests for base models."""

from mcp_server.models.base import BaseModelConfig
from pydantic import BaseModel


def test_base_model_config_exists():
    """BaseModelConfig should be defined and inherit from BaseModel."""
    assert issubclass(BaseModelConfig, BaseModel)


def test_base_model_config_can_subclass():
    """Should be able to subclass BaseModelConfig."""

    class DummyModel(BaseModelConfig):
        name: str
        value: int = 0

    instance = DummyModel(name="test")
    assert instance.name == "test"
    assert instance.value == 0


def test_base_model_config_instance():
    """BaseModelConfig itself should be instantiable (empty)."""
    instance = BaseModelConfig()
    assert isinstance(instance, BaseModelConfig)