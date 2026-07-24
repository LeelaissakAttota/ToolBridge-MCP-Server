import pytest
import asyncio
from mcp_server.orchestrator.task_queue import TaskQueue
from mcp_server.orchestrator.models import Task, TaskPriority, TaskStatus


@pytest.fixture
def task_queue():
    return TaskQueue()


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
async def test_enqueue_dequeue(task_queue, sample_task):
    await task_queue.enqueue(sample_task)
    assert await task_queue.get_queue_size() == 1
    task = await task_queue.dequeue()
    assert task is not None
    assert task.id == sample_task.id
    assert task.status == TaskStatus.RUNNING  # Because dequeue sets it to RUNNING
    assert await task_queue.get_queue_size() == 0