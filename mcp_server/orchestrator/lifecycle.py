"""Lifecycle Manager for the AI Agent Orchestrator."""

import asyncio
import logging
from typing import Dict, Optional
from .models import AgentStatus
from .exceptions import InvalidStateTransitionError


logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages the lifecycle of agents with state transitions."""

    def __init__(self):
        self._agent_states: Dict[str, AgentStatus] = {}
        self._lock = asyncio.Lock()

    # Define valid state transitions
    _VALID_TRANSITIONS = {
        AgentStatus.CREATED: [AgentStatus.INITIALIZED],
        AgentStatus.INITIALIZED: [AgentStatus.STARTING, AgentStatus.STOPPED],
        AgentStatus.STARTING: [AgentStatus.RUNNING, AgentStatus.FAILED],
        AgentStatus.RUNNING: [AgentStatus.BUSY, AgentStatus.IDLE, AgentStatus.STOPPING],
        AgentStatus.BUSY: [AgentStatus.RUNNING, AgentStatus.IDLE],
        AgentStatus.IDLE: [AgentStatus.RUNNING, AgentStatus.BUSY],
        AgentStatus.STOPPING: [AgentStatus.STOPPED, AgentStatus.FAILED],
        AgentStatus.STOPPED: [AgentStatus.RESTARTING],
        AgentStatus.RESTARTING: [AgentStatus.STARTING],
        AgentStatus.FAILED: [AgentStatus.RESTARTING, AgentStatus.STOPPED],
    }

    async def initialize_agent(self, agent_info) -> None:
        """Initialize an agent (CREATED -> INITIALIZED).
        
        Args:
            agent_info: The agent to initialize
            
        Raises:
            InvalidStateTransitionError: If the agent is not in CREATED state
        """
        async with self._lock:
            await self._validate_transition(agent_info.id, agent_info.status, AgentStatus.INITIALIZED)
            agent_info.status = AgentStatus.INITIALIZED
            self._agent_states[agent_info.id] = AgentStatus.INITIALIZED
            logger.info(f"Initialized agent: {agent_info.id}")

    async def start_agent(self, agent_info) -> None:
        """Start an agent (INITIALIZED -> STARTING -> RUNNING).
        
        Args:
            agent_info: The agent to start
            
        Raises:
            InvalidStateTransitionError: If the agent is not in INITIALIZED state
        """
        async with self._lock:
            await self._validate_transition(agent_info.id, agent_info.status, AgentStatus.STARTING)
            agent_info.status = AgentStatus.STARTING
            self._agent_states[agent_info.id] = AgentStatus.STARTING
            
            # Simulate startup process
            await self._perform_startup(agent_info)
            
            agent_info.status = AgentStatus.RUNNING
            self._agent_states[agent_info.id] = AgentStatus.RUNNING
            logger.info(f"Started agent: {agent_info.id}")

    async def _perform_startup(self, agent_info) -> None:
        """Perform agent startup operations.
        
        This is a placeholder for actual startup logic (e.g., loading models, connecting to services).
        """
        # In a real implementation, this would call agent.initialize() or similar
        await asyncio.sleep(0.01)  # Simulate async work

    async def set_agent_busy(self, agent_info) -> None:
        """Set an agent as busy (RUNNING -> BUSY).
        
        Args:
            agent_info: The agent to set as busy
            
        Raises:
            InvalidStateTransitionError: If the agent is not in RUNNING state
        """
        async with self._lock:
            await self._validate_transition(agent_info.id, agent_info.status, AgentStatus.BUSY)
            agent_info.status = AgentStatus.BUSY
            self._agent_states[agent_info.id] = AgentStatus.BUSY
            logger.debug(f"Set agent busy: {agent_info.id}")

    async def set_agent_idle(self, agent_info) -> None:
        """Set an agent as idle (BUSY -> RUNNING).
        
        Args:
            agent_info: The agent to set as idle
            
        Raises:
            InvalidStateTransitionError: If the agent is not in BUSY state
        """
        async with self._lock:
            await self._validate_transition(agent_info.id, agent_info.status, AgentStatus.RUNNING)
            agent_info.status = AgentStatus.RUNNING
            self._agent_states[agent_info.id] = AgentStatus.RUNNING
            logger.debug(f"Set agent idle: {agent_info.id}")

    async def stop_agent(self, agent_info) -> None:
        """Stop an agent (RUNNING -> STOPPING -> STOPPED).
        
        Args:
            agent_info: The agent to stop
            
        Raises:
            InvalidStateTransitionError: If the agent is not in RUNNING state
        """
        async with self._lock:
            await self._validate_transition(agent_info.id, agent_info.status, AgentStatus.STOPPING)
            agent_info.status = AgentStatus.STOPPING
            self._agent_states[agent_info.id] = AgentStatus.STOPPING
            
            # Simulate shutdown process
            await self._perform_shutdown(agent_info)
            
            agent_info.status = AgentStatus.STOPPED
            self._agent_states[agent_info.id] = AgentStatus.STOPPED
            logger.info(f"Stopped agent: {agent_info.id}")

    async def _perform_shutdown(self, agent_info) -> None:
        """Perform agent shutdown operations.
        
        This is a placeholder for actual shutdown logic (e.g., saving state, closing connections).
        """
        # In a real implementation, this would call agent.shutdown() or similar
        await asyncio.sleep(0.01)  # Simulate async work

    async def fail_agent(self, agent_info) -> None:
        """Mark an agent as failed (any state -> FAILED).
        
        Args:
            agent_info: The agent to mark as failed
        """
        async with self._lock:
            # Allow transition to FAILED from any state except FAILED itself
            if agent_info.status != AgentStatus.FAILED:
                agent_info.status = AgentStatus.FAILED
                self._agent_states[agent_info.id] = AgentStatus.FAILED
                logger.error(f"Agent failed: {agent_info.id}")

    async def restart_agent(self, agent_info) -> None:
        """Restart an agent (STOPPED -> RESTARTING -> STARTING -> RUNNING).
        
        Args:
            agent_info: The agent to restart
            
        Raises:
            InvalidStateTransitionError: If the agent is not in STOPPED state
        """
        async with self._lock:
            await self._validate_transition(agent_info.id, agent_info.status, AgentStatus.RESTARTING)
            agent_info.status = AgentStatus.RESTARTING
            self._agent_states[agent_info.id] = AgentStatus.RESTARTING
            logger.info(f"Restarting agent: {agent_info.id}")
            
            # Perform restart sequence
            await self.start_agent(agent_info)

    async def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get the current status of an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            AgentStatus: The current status of the agent
        """
        async with self._lock:
            return self._agent_states.get(agent_id, AgentStatus.CREATED)

    async def reset_agent(self, agent_info) -> None:
        """Reset an agent to CREATED state (any state -> CREATED).
        
        Args:
            agent_info: The agent to reset
        """
        async with self._lock:
            agent_info.status = AgentStatus.CREATED
            self._agent_states[agent_info.id] = AgentStatus.CREATED
            logger.info(f"Reset agent: {agent_info.id}")

    async def can_transition(self, agent_id: str, from_state: AgentStatus, to_state: AgentStatus) -> bool:
        """Check if a state transition is valid.
        
        Args:
            agent_id: The ID of the agent
            from_state: The current state
            to_state: The target state
            
        Returns:
            bool: True if the transition is valid, False otherwise
        """
        async with self._lock:
            current_state = self._agent_states.get(agent_id, AgentStatus.CREATED)
            if current_state != from_state:
                return False
            return to_state in self._VALID_TRANSITIONS.get(from_state, [])

    async def _validate_transition(self, agent_id: str, current_state: AgentStatus, target_state: AgentStatus) -> None:
        """Validate that a state transition is allowed.
        
        Args:
            agent_id: The ID of the agent
            current_state: The current state of the agent
            target_state: The target state for the transition
            
        Raises:
            InvalidStateTransitionError: If the transition is not allowed
        """
        if target_state not in self._VALID_TRANSITIONS.get(current_state, []):
            raise InvalidStateTransitionError(
                agent_id=agent_id,
                current_state=current_state.value,
                required_state=target_state.value
            )