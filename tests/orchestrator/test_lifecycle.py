import pytest
import asyncio
from unittest.mock import Mock
from mcp_server.orchestrator.lifecycle import LifecycleManager
from mcp_server.orchestrator.models import AgentInfo, AgentStatus, AgentCapability, AgentMetadata
from mcp_server.orchestrator.exceptions import InvalidStateTransitionError


@pytest.fixture
def lifecycle_manager():
    return LifecycleManager()


@pytest.fixture
def sample_agent():
    return AgentInfo(
        id="test-agent",
        name="Test Agent",
        description="A test agent",
        capabilities=[AgentCapability(name="test-cap", description="Test capability")],
        status=AgentStatus.CREATED,
        metadata=AgentMetadata()
    )


@pytest.mark.asyncio
async def test_initialize_agent(lifecycle_manager, sample_agent):
    await lifecycle_manager.initialize_agent(sample_agent)
    assert sample_agent.status == AgentStatus.INITIALIZED


@pytest.mark.asyncio
async def test_start_agent(lifecycle_manager, sample_agent):
    await lifecycle_manager.initialize_agent(sample_agent)
    await lifecycle_manager.start_agent(sample_agent)
    assert sample_agent.status == AgentStatus.RUNNING


@pytest.mark.asyncio
async def test_set_agent_busy(lifecycle_manager, sample_agent):
    await lifecycle_manager.initialize_agent(sample_agent)
    await lifecycle_manager.start_agent(sample_agent)
    await lifecycle_manager.set_agent_busy(sample_agent)
    assert sample_agent.status == AgentStatus.BUSY


@pytest.mark.asyncio
async def test_set_agent_idle(lifecycle_manager, sample_agent):
    await lifecycle_manager.initialize_agent(sample_agent)
    await lifecycle_manager.start_agent(sample_agent)
    await lifecycle_manager.set_agent_busy(sample_agent)
    await lifecycle_manager.set_agent_idle(sample_agent)
    assert sample_agent.status == AgentStatus.RUNNING


@pytest.mark.asyncio
async def test_stop_agent(lifecycle_manager, sample_agent):
    await lifecycle_manager.initialize_agent(sample_agent)
    await lifecycle_manager.start_agent(sample_agent)
    await lifecycle_manager.stop_agent(sample_agent)
    assert sample_agent.status == AgentStatus.STOPPED


@pytest.mark.asyncio
async def test_invalid_transition(lifecycle_manager, sample_agent):
    # Try to go from CREATED directly to BUSY (should fail)
    with pytest.raises(Exception):  # InvalidStateTransitionError
        await lifecycle_manager.set_agent_busy(sample_agent)


@pytest.mark.asyncio
async def test_get_agent_status(lifecycle_manager, sample_agent):
    status = await lifecycle_manager.get_agent_status(sample_agent.id)
    assert status == AgentStatus.CREATED
    
    await lifecycle_manager.initialize_agent(sample_agent)
    status = await lifecycle_manager.get_agent_status(sample_agent.id)
    assert status == AgentStatus.INITIALIZED


@pytest.mark.asyncio
async def test_can_transition(lifecycle_manager, sample_agent):
    # CREATED -> INITIALIZED should be allowed
    assert await lifecycle_manager.can_transition(
        sample_agent.id, 
        AgentStatus.CREATED, 
        AgentStatus.INITIALIZED
    ) == True
    
    # CREATED -> BUSY should not be allowed
    assert await lifecycle_manager.can_transition(
        sample_agent.id, 
        AgentStatus.CREATED, 
        AgentStatus.BUSY
    ) == False


@pytest.mark.asyncio
async def test_reset_agent(lifecycle_manager, sample_agent):
    await lifecycle_manager.initialize_agent(sample_agent)
    await lifecycle_manager.start_agent(sample_agent)
    await lifecycle_manager.set_agent_busy(sample_agent)
    
    await lifecycle_manager.reset_agent(sample_agent)
    assert sample_agent.status == AgentStatus.CREATED