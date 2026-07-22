"""Tests for ProviderBase abstract class."""

import pytest
from mcp_server.providers.base import ProviderBase


def test_provider_base_is_abstract():
    """ProviderBase should be an abstract base class."""
    assert hasattr(ProviderBase, '__abstractmethods__')
    assert 'connect' in ProviderBase.__abstractmethods__
    assert 'close' in ProviderBase.__abstractmethods__


def test_provider_base_cannot_instantiate():
    """Direct instantiation of ProviderBase should raise TypeError."""
    with pytest.raises(TypeError):
        ProviderBase()


def test_provider_base_subclass_must_implement():
    """Subclass without implementing abstract methods should raise TypeError."""

    class IncompleteProvider(ProviderBase):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_provider_base_concrete_subclass():
    """Fully implemented subclass should be instantiable."""

    class ConcreteProvider(ProviderBase):
        def connect(self) -> None:
            self.connected = True

        def close(self) -> None:
            self.connected = False

    provider = ConcreteProvider()
    provider.connect()
    assert provider.connected is True
    provider.close()
    assert provider.connected is False