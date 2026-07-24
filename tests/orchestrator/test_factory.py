import pytest
import asyncio
from unittest.mock import Mock
from mcp_server.orchestrator.factory import AgentFactory
from mcp_server.orchestrator.models import AgentInfo, AgentCapability, AgentMetadata
from mcp_server.orchestrator.exceptions import ConfigurationError


@pytest.fixture
def factory():
    return AgentFactory()


class MockAgent:
    def __init__(self, agent_id, name, description="", capabilities=None, 
                 configuration=None, metadata=None, **kwargs):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.configuration = configuration or {}
        self.metadata = metadata or {}
        # Store any additional dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_register_agent_class(factory):
    factory.register_agent_class("mock", MockAgent)
    assert factory.is_agent_type_registered("mock")
    assert "mock" in factory.get_registered_agent_types()


@pytest.mark.asyncio
async def test_create_agent(factory):
    factory.register_agent_class("mock", MockAgent)
    
    agent_info = await factory.create_agent(
        agent_type="mock",
        agent_id="test-agent",
        name="Test Agent",
        description="A test agent",
        capabilities=[AgentCapability(name="test-cap", description="Test capability")],
        configuration={"setting": "value"},
        metadata={"version": "1.0.0", "author": "test"}
    )
    
    assert agent_info.id == "test-agent"
    assert agent_info.name == "Test Agent"
    assert agent_info.description == "A test agent"
    assert len(agent_info.capabilities) == 1
    assert agent_info.capabilities[0].name == "test-cap"
    assert agent_info.metadata.author == "test"


@pytest.mark.asyncio
async def test_create_agent_from_config(factory):
    factory.register_agent_class("mock", MockAgent)
    
    config = {
        "type": "mock",
        "id": "config-agent",
        "name": "Config Agent",
        "description": "Agent from config",
        "capabilities": [AgentCapability(name="config-cap", description="Config capability")],
        "configuration": {"debug": True},
        "metadata": {"version": "2.0.0", "author": "test"}
    }
    
    agent_info = await factory.create_agent_from_config(config)
    
    assert agent_info.id == "config-agent"
    assert agent_info.name == "Config Agent"
    assert agent_info.description == "Agent from config"
    assert len(agent_info.capabilities) == 1
    assert agent_info.capabilities[0].name == "config-cap"
    assert agent_info.metadata.author == "test"


@pytest.mark.asyncio
async def test_create_agent_unregistered_type(factory):
    with pytest.raises(ConfigurationError):
        await factory.create_agent("unknown-type", {}, {}, {}, {}, {})


@pytest.mark.asyncio
async def test_create_agent_from_config_missing_type(factory):
    agent_config = {
        "config": {"param": "value"},
        "id": "test-agent-1"
    }
    
    with pytest.raises(ConfigurationError):
        await factory.create_agent_from_config(agent_config)


@pytest.mark.asyncio
async def test_unregister_agent_class(factory):
    factory.register_agent_class("mock", MockAgent)
    assert factory.is_agent_type_registered("mock")
    
    factory.unregister_agent_class("mock")
    assert not factory.is_agent_type_registered("mock")