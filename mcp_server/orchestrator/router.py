"""Task Router for the AI Agent Orchestrator."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from .models import AgentInfo, AgentStatus, Task, TaskPriority
from .registry import AgentRegistry
from .task_queue import TaskQueue


logger = logging.getLogger(__name__)


class TaskRouter:
    """Routes tasks to appropriate agents based on capability, priority, availability, and workload."""

    def __init__(self, registry: AgentRegistry, task_queue: TaskQueue):
        self._registry = registry
        self._task_queue = task_queue
        self._last_assigned_agent: Dict[str, int] = {}  # capability -> last index used for round-robin
        self._lock = asyncio.Lock()

    async def enqueue_task(self, task: Task) -> None:
        """Add a task to the routing queue.
        
        Args:
            task: The task to enqueue
        """
        await self._task_queue.enqueue(task)

    async def dequeue_task(self) -> Optional[Task]:
        """Remove and return the highest priority task from the queue.
        
        Returns:
            The highest priority task, or None if queue is empty
        """
        return await self._task_queue.dequeue()

    async def route_task(self) -> Optional[tuple[AgentInfo, Task]]:
        """Route the highest priority task to an available agent.
        
        Returns:
            Tuple of (agent, task) if a task could be routed, None if no task or no available agent
        """
        async with self._lock:
            # Get the highest priority task from the queue
            task = await self._task_queue.dequeue()
            if task is None:
                return None

            # Find agents that have the required capability
            capable_agents = await self._registry.discover_agents_by_capability(task.capability_required)
            
            # Filter agents that are available (running and not currently busy)
            available_agents = [
                agent for agent in capable_agents
                if agent.status == AgentStatus.RUNNING and agent.current_task_id is None
            ]

            if not available_agents:
                # No available agent, put the task back in the queue
                await self._task_queue.enqueue(task)
                logger.warning(f"No available agent for task {task.id} requiring capability '{task.capability_required}'")
                return None

            # Select agent using round-robin per capability for workload balancing
            capability = task.capability_required
            if capability not in self._last_assigned_agent:
                self._last_assigned_agent[capability] = 0

            # Get list of available agent IDs for this capability
            available_agent_ids = [agent.id for agent in available_agents]
            last_index = self._last_assigned_agent[capability]
            selected_index = (len(available_agents) + last_index) % len(available_agents)
            selected_agent_id = available_agent_ids[selected_index]
            self._last_assigned_agent[capability] = selected_index

            # Find the selected agent object
            selected_agent = next(
                agent for agent in available_agents if agent.id == selected_agent_id
            )

            logger.info(
                f"Routed task {task.id} (priority: {task.priority.name}) "
                f"to agent {selected_agent.id} (capability: {task.capability_required})"
            )
            return (selected_agent, task)

    async def peek_next_task(self) -> Optional[Task]:
        """Peek at the next highest priority task without removing it from the queue.
        
        Returns:
            The next task if available, None otherwise
        """
        return await self._task_queue.peek()

    async def get_task_count(self) -> int:
        """Get the total number of tasks in the queue.
        
        Returns:
            Number of tasks in the queue
        """
        return await self._task_queue.get_queue_size()

    async def get_task_count_by_priority(self) -> dict[TaskPriority, int]:
        """Get the number of tasks in the queue by priority level.
        
        Returns:
            Dictionary mapping priority levels to counts
        """
        return await self._task_queue.get_queue_size_by_priority()

    async def clear_route_cache(self) -> None:
        """Clear the routing cache (used for testing or reset)."""
        async with self._lock:
            self._last_assigned_agent.clear()