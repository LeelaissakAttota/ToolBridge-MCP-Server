"""Task Queue for the AI Agent Orchestrator."""

import asyncio
import heapq
import logging
from typing import Dict, List, Optional, Tuple
from .models import Task, TaskPriority, TaskStatus


logger = logging.getLogger(__name__)


class TaskQueue:
    """Async-safe priority queue for tasks."""

    def __init__(self):
        self._queue: List[Tuple[int, int, Task]] = []  # (priority, insertion_order, task)
        self._task_map: Dict[str, Tuple[int, int, Task]] = {}  # task_id -> entry in queue
        self._insertion_order = 0
        self._lock = asyncio.Lock()

    async def enqueue(self, task: Task) -> None:
        """Add a task to the queue.
        
        Args:
            task: The task to enqueue
        """
        async with self._lock:
            # Remove if already exists (update scenario)
            if task.id in self._task_map:
                await self.remove_task(task.id)
            
            # Priority: higher priority value = higher priority (negated for min-heap)
            priority = -task.priority.value
            entry = (priority, self._insertion_order, task)
            self._task_map[task.id] = entry
            heapq.heappush(self._queue, entry)
            self._insertion_order += 1
            logger.debug(f"Enqueued task {task.id} with priority {task.priority.name}")

    async def dequeue(self) -> Optional[Task]:
        """Remove and return the highest priority task.
        
        Returns:
            The highest priority task, or None if queue is empty
        """
        async with self._lock:
            while self._queue:
                # Peek at the first item without popping
                entry = self._queue[0]  # Don't pop yet
                priority, order, task = entry
                
                # Check if this task has been removed (stale entry)
                if task.id in self._task_map and self._task_map[task.id] is entry:
                    # This is a valid entry, remove it from heap and map
                    heapq.heappop(self._queue)
                    del self._task_map[task.id]
                    # Update task status to running when dequeued for processing
                    task.status = TaskStatus.RUNNING
                    logger.debug(f"Dequeued task {task.id}")
                    return task
                else:
                    # This is a stale entry, remove it from heap and continue
                    heapq.heappop(self._queue)
            return None

    async def peek(self) -> Optional[Task]:
        """Return the highest priority task without removing it.
        
        Returns:
            The highest priority task, or None if queue is empty
        """
        async with self._lock:
            while self._queue:
                # Peek at the first item without popping
                entry = self._queue[0]  # Don't pop yet
                priority, order, task = entry
                
                # Check if this task has been removed (stale entry)
                if task.id in self._task_map and self._task_map[task.id] is entry:
                    return task
                else:
                    # This is a stale entry, remove it from heap and continue
                    heapq.heappop(self._queue)
            return None

    async def remove_task(self, task_id: str) -> bool:
        """Remove a specific task from the queue by ID.
        
        Args:
            task_id: The ID of the task to remove
            
        Returns:
            True if task was found and removed, False otherwise
        """
        async with self._lock:
            entry = self._task_map.pop(task_id, None)
            if entry is None:
                return False
            # Remove the entry from the heap by marking it as stale
            # It will be skipped when encountered in dequeue/peek
            logger.debug(f"Removed task {task_id} from queue")
            return True

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task from the queue by ID without removing it.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            The task if found, None otherwise
        """
        async with self._lock:
            entry = self._task_map.get(task_id)
            if entry is None:
                return None
            return entry[2]  # The task object

    async def update_task(self, task_id: str, new_task: Task) -> bool:
        """Update an existing task in the queue.
        
        Args:
            task_id: The ID of the task to update
            new_task: The new task data
            
        Returns:
            True if task was found and updated, False otherwise
        """
        async with self._lock:
            if task_id not in self._task_map:
                return False
            # Remove old and add new
            await self.remove_task(task_id)
            await self.enqueue(new_task)
            logger.debug(f"Updated task {task_id}")
            return True

    async def get_queue_size(self) -> int:
        """Get the number of tasks in the queue.
        
        Returns:
            Number of tasks in the queue
        """
        async with self._lock:
            return len(self._task_map)

    async def get_queue_size_by_priority(self) -> dict[TaskPriority, int]:
        """Get the number of tasks in the queue by priority level.
        
        Returns:
            Dictionary mapping priority levels to counts
        """
        async with self._lock:
            counts = {priority: 0 for priority in TaskPriority}
            for _, _, task in self._task_map.values():
                counts[task.priority] += 1
            return counts

    async def is_empty(self) -> bool:
        """Check if the queue is empty.
        
        Returns:
            True if queue is empty, False otherwise
        """
        async with self._lock:
            return len(self._task_map) == 0

    async def clear(self) -> None:
        """Remove all tasks from the queue."""
        async with self._lock:
            self._queue.clear()
            self._task_map.clear()
            self._insertion_order = 0
            logger.debug("Cleared all tasks from queue")