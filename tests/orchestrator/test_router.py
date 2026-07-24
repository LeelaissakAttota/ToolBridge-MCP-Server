import pytest
import asyncio
from unittest.mock import AsyncMock
from mcp_server.orchestrator.router import TaskRouter
from mcp_server.orchestrator.models import Task, TaskPriority, AgentInfo, AgentStatus, AgentCapability, AgentMetadata
from mcp_server.orchestrator.registry import AgentRegistry
from mcp_server.orchestrator.task_queue import TaskQueue


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def task_queue():
    return TaskQueue()


@pytest.fixture
def router(registry, task_queue):
    return TaskRouter(registry, task_queue)


@pytest.fixture
def sample_agent():
    return AgentInfo(
        id="test-agent-1",
        name="Test Agent 1",
        description="A test agent",
        capabilities=[AgentCapability(name="test-cap", description="Test capability")],
        status=AgentStatus.RUNNING,
        metadata=AgentMetadata()
    )


@pytest.fixture
def sample_task():
    return Task(
        id="test-task-1",
        name="Test Task 1",
        description="A test task",
        capability_required="test-cap",
        priority=TaskPriority.MEDIUM,
        payload={"data": "test"}
    )


@pytest.mark.asyncio
async def test_enqueue_task(router, sample_task):
    await router.enqueue_task(sample_task)
    assert await router.get_task_count() == 1


@pytest.mark.asyncio
async def test_enqueue_multiple_tasks(router, sample_task):
    task2 = sample_task.copy()
    task2.id = "test-task-2"
    
    await router.enqueue_task(sample_task)
    await router.enqueue_task(task2)
    assert await router.get_task_count() == 2


@pytest.mark.asyncio
async def test_dequeue_task(router, sample_task):
    await router.enqueue_task(sample_task)
    task = await router.dequeue_task()
    assert task is not None
    assert task.id == sample_task.id
    assert await router.get_task_count() == 0


@pytest.mark.asyncio
async def test_dequeue_empty_queue(router):
    task = await router.dequeue_task()
    assert task is None


@pytest.mark.asyncio
async def test_peek_next_task(router, sample_task):
    await router.enqueue_task(sample_task)
    task = await router.peek_next_task()
    assert task is not None
    assert task.id == sample_task.id
    # Queue should still have the task
    assert await router.get_task_count() == 1


@pytest.mark.asyncio
async def test_priority_ordering(router):
    # Create tasks with different priorities
    task_low = Task(
        id="low",
        name="Low Priority",
        description="Low priority task",
        capability_required="test-cap",
        priority=TaskPriority.LOW,
        payload={}
    )
    
    task_high = Task(
        id="high",
        name="High Priority",
        description="High priority task",
        capability_required="test-cap",
        priority=TaskPriority.HIGH,
        payload={}
    )
    
    # Enqueue low priority first, then high priority
    await router.enqueue_task(task_low)
    await router.enqueue_task(task_high)
    
    # Dequeue should return high priority first
    task = await router.dequeue_task()
    assert task.id == "high"
    
    task = await router.dequeue_task()
    assert task.id == "low"


@pytest.mark.asyncio
async def test_route_task_no_agents(router, sample_task):
    # Try to route a task when no agents are registered
    await router.enqueue_task(sample_task)
    result = await router.route_task()
    assert result is None  # No agents available
    # Task should still be in queue
    assert await router.get_task_count() == 1


@pytest.mark.asyncio
async def test_route_task_with_agent(router, registry, sample_agent, sample_task):
    # Register an agent
    await registry.register_agent(sample_agent)
    
    # Enqueue a task
    await router.enqueue_task(sample_task)
    
    # Route the task
    result = await router.route_task()
    assert result is not None
    agent, task = result
    assert agent.id == sample_agent.id
    assert task.id == sample_task.id
    # Task should be removed from queue
    assert await router.get_task_count() == 0


@pytest.mark.asyncio
async def test_route_task_agent_busy(router, registry, sample_agent, sample_task):
    # Register an agent but mark it as busy
    sample_agent.status = AgentStatus.BUSY
    sample_agent.current_task_id = "some-other-task"
    await registry.register_agent(sample_agent)
    
    # Enqueue a task
    await router.enqueue_task(sample_task)
    
    # Route the task - should return None because agent is busy
    result = await router.route_task()
    assert result is None
    # Task should still be in queue
    assert await router.get_task_count() == 1


@pytest.mark.asyncio
async def test_route_task_wrong_capability(router, registry, sample_agent, sample_task):
    # Register an agent with wrong capability
    wrong_agent = sample_agent.copy()
    wrong_agent.id = "wrong-agent"
    wrong_agent.capabilities = [AgentCapability(name="wrong-cap", description="Wrong capability")]
    await registry.register_agent(wrong_agent)
    
    # Enqueue a task
    await router.enqueue_task(sample_task)
    
    # Route the task - should return None because no agent has the right capability
    result = await router.route_task()
    assert result is None
    # Task should still be in queue
    assert await router.get_task_count() == 1


@pytest.mark.asyncio
async def test_peek_next_task(router, sample_task):
    await router.enqueue_task(sample_task)
    task = await router.peek_next_task()
    assert task is not None
    assert task.id == sample_task.id
    # Queue should still have the task
    assert await router.get_task_count() == 1


@pytest.mark.asyncio
async def test_peek_next_task_empty(router):
    task = await router.peek_next_task()
    assert task is None