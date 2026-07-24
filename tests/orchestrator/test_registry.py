import pytest
import asyncio
from mcp_server.orchestrator.registry import AgentRegistry
from mcp_server.orchestrator.models import AgentInfo, AgentCapability, AgentMetadata
from mcp_server.orchestrator.exceptions import AgentAlreadyExistsError, AgentNotFoundError


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def sample_agent():
    return AgentInfo(
        id="test-agent",
        name="Test Agent",
        description="A test agent",
        capabilities=[AgentCapability(name="test-capability", description="A test capability")],
        metadata=AgentMetadata(version="1.0.0", author="test")
    )


@pytest.mark.asyncio
async def test_register_agent(registry, sample_agent):
    await registry.register_agent(sample_agent)
    assert await registry.get_agent_count() == 1
    retrieved = await registry.get_agent("test-agent")
    assert retrieved.id == sample_agent.id
    assert retrieved.name == sample_agent.name


@pytest.mark.asyncio
async def test_register_duplicate_agent(registry, sample_agent):
    await registry.register_agent(sample_agent)
    with pytest.raises(AgentAlreadyExistsError):
        await registry.register_agent(sample_agent)


@pytest.mark.asyncio
async def test_get_agent_not_found(registry):
    with pytest.raises(AgentNotFoundError):
        await registry.get_agent("non-existent")


@pytest.mark.asyncio
async def test_unregister_agent(registry, sample_agent):
    await registry.register_agent(sample_agent)
    await registry.unregister_agent("test-agent")
    assert await registry.get_agent_count() == 0
    with pytest.raises(AgentNotFoundError):
        await registry.get_agent("test-agent")


@pytest.mark.asyncio
async def test_update_agent(registry, sample_agent):
    await registry.register_agent(sample_agent)
    updated_agent = sample_agent.copy()
    updated_agent.name = "Updated Agent"
    await registry.update_agent(updated_agent)
    retrieved = await registry.get_agent("test-agent")
    assert retrieved.name == "Updated Agent"


@pytest.mark.asyncio
async def test_list_agents(registry, sample_agent):
    await registry.register_agent(sample_agent)
    agents = await registry.list_agents()
    assert len(agents) == 1
    assert agents[0].id == "test-agent"


@pytest.mark.asyncio
async def test_discover_agents_by_capability(registry, sample_agent):
    await registry.register_agent(sample_agent)
    agents = await registry.discover_agents_by_capability("test-capability")
    assert len(agents) == 1
    assert agents[0].id == "test-agent"


@pytest.mark.asyncio
async def test_discover_agents_by_capabilities(registry, sample_agent):
    await registry.register_agent(sample_agent)
    agents = await registry.discover_agents_by_capabilities(["test-capability"])
    assert len(agents) == 1
    assert agents[0].id == "test-agent"


@pytest.mark.asyncio
async def test_get_agent_count(registry, sample_agent):
    assert await registry.get_agent_count() == 0
    await registry.register_agent(sample_agent)
    assert await registry.get_agent_count() == 1


@pytest.mark.asyncio
async def test_clear_registry(registry, sample_agent):
    await registry.register_agent(sample_agent)
    await registry.clear()
    assert await registry.get_agent_count() == 0
