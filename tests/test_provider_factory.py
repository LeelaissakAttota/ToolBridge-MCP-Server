"""Tests for ProviderFactory."""

import pytest
from mcp_server.providers.factory import ProviderFactory
from mcp_server.providers.base import ProviderConfig


def test_factory_initialization():
    """Factory should initialize with empty instances."""
    factory = ProviderFactory()
    assert len(factory._instances) == 0
    assert len(factory._provider_classes) > 0


def test_list_provider_classes():
    """Factory should list built-in provider classes."""
    factory = ProviderFactory()
    classes = factory.list_provider_classes()
    assert "cerebras" in classes
    assert "nvidia" in classes
    assert "openrouter" in classes


def test_get_provider_class():
    """Should retrieve provider class by name."""
    factory = ProviderFactory()
    from mcp_server.providers.cerebras import CerebrasProvider
    assert factory.get_provider_class("cerebras") == CerebrasProvider


def test_get_provider_class_not_found():
    """Should raise KeyError for unknown provider."""
    factory = ProviderFactory()
    with pytest.raises(KeyError):
        factory.get_provider_class("unknown")


def test_register_custom_provider():
    """Should be able to register custom provider class."""
    factory = ProviderFactory()

    class CustomProvider:
        pass

    factory.register("custom", CustomProvider)
    assert "custom" in factory.list_provider_classes()


def test_unregister_provider():
    """Should be able to unregister provider class."""
    factory = ProviderFactory()
    factory.register("to_remove", object)
    assert factory.unregister("to_remove") is True
    assert "to_remove" not in factory.list_provider_classes()


def test_unregister_nonexistent():
    """Unregistering non-existent should return False."""
    factory = ProviderFactory()
    assert factory.unregister("nonexistent") is False


def test_create_provider():
    """Should create provider instance with config."""
    factory = ProviderFactory()
    config = ProviderConfig(api_key="test-key", default_model="test-model")
    instance = factory.create("cerebras", config)
    assert instance is not None
    assert instance.name == "cerebras"
    assert instance.config.api_key == "test-key"


def test_create_provider_not_found():
    """Creating unknown provider should raise KeyError."""
    factory = ProviderFactory()
    with pytest.raises(KeyError):
        factory.create("unknown")


def test_get_or_create_singleton():
    """get_or_create should return same instance."""
    factory = ProviderFactory()
    config = ProviderConfig(api_key="test", default_model="model")

    inst1 = factory.get_or_create("cerebras", config)
    inst2 = factory.get_or_create("cerebras", config)

    assert inst1 is inst2


def test_register_instance():
    """Should be able to register existing instance."""
    factory = ProviderFactory()

    class MockProvider:
        name = "mock"

    provider = MockProvider()
    factory.register_instance("mock", provider)
    assert factory.get_instance("mock") is provider


def test_unregister_instance():
    """Should be able to unregister instance."""
    factory = ProviderFactory()

    class MockProvider:
        name = "mock"

    factory.register_instance("mock", MockProvider())
    assert factory.unregister_instance("mock") is True
    assert factory.get_instance("mock") is None


def test_get_instance():
    """Should retrieve instance by name."""
    factory = ProviderFactory()

    class MockProvider:
        name = "mock"

    factory.register_instance("mock", MockProvider())
    assert factory.get_instance("mock") is not None


def test_get_nonexistent_instance():
    """Getting non-existent instance should return None."""
    factory = ProviderFactory()
    assert factory.get_instance("nonexistent") is None


def test_list_instances():
    """Should list all instance names."""
    factory = ProviderFactory()

    class MockProvider:
        name = "mock"

    factory.register_instance("mock", MockProvider())
    assert "mock" in factory.list_instances()


def test_clear_instances():
    """Should clear all instances."""
    factory = ProviderFactory()

    class MockProvider:
        name = "mock"

    factory.register_instance("mock", MockProvider())
    factory.clear_instances()
    assert len(factory.list_instances()) == 0


def test_list_provider_classes():
    """Should list available provider class names."""
    factory = ProviderFactory()
    classes = factory.list_provider_classes()
    assert "cerebras" in classes
    assert "nvidia" in classes
    assert "openrouter" in classes


def test_contains_provider():
    """Should support 'in' operator."""
    factory = ProviderFactory()
    assert "cerebras" in factory


def test_factory_repr():
    """Factory should have readable repr."""
    factory = ProviderFactory()
    repr_str = repr(factory)
    assert "ProviderFactory" in repr_str


def test_provider_config_type_acceptance():
    """create() should accept both dict and ProviderConfig."""
    factory = ProviderFactory()

    # With dict
    instance1 = factory.create("cerebras", {"api_key": "test", "default_model": "test"})

    # With ProviderConfig
    config = ProviderConfig(api_key="test", default_model="model")
    instance2 = factory.create("cerebras", config)

    assert instance1 is not None
    assert instance2 is not None


def test_provider_config_from_dict():
    """ProviderConfig should be creatable from dict."""
    config_dict = {
        "api_key": "test-key",
        "base_url": "https://api.test.com",
        "timeout": 60.0,
        "max_retries": 5,
        "default_model": "test-model",
    }
    config = ProviderConfig(**config_dict)
    assert config.api_key == "test-key"
    assert config.base_url == "https://api.test.com"
    assert config.timeout == 60.0
    assert config.max_retries == 5
    assert config.default_model == "test-model"