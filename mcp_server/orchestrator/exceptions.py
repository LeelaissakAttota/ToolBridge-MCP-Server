"""Exception hierarchy for the AI Agent Orchestrator."""

from typing import Any, Dict, Optional


class OrchestratorError(Exception):
    """Base exception for all orchestrator-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AgentNotFoundError(OrchestratorError):
    """Raised when an agent is not found in the registry."""
    
    def __init__(self, agent_id: str):
        super().__init__(
            f"Agent not found: {agent_id}",
            {"agent_id": agent_id}
        )


class AgentAlreadyExistsError(OrchestratorError):
    """Raised when attempting to register an agent that already exists."""
    
    def __init__(self, agent_id: str):
        super().__init__(
            f"Agent already exists: {agent_id}",
            {"agent_id": agent_id}
        )


class InvalidAgentStateError(OrchestratorError):
    """Raised when an agent is in an invalid state for the requested operation."""
    
    def __init__(self, agent_id: str, current_state: str, required_state: str):
        super().__init__(
            f"Agent {agent_id} is in invalid state '{current_state}', required state: '{required_state}'",
            {
                "agent_id": agent_id,
                "current_state": current_state,
                "required_state": required_state
            }
        )


class InvalidStateTransitionError(OrchestratorError):
    """Raised when attempting an invalid state transition."""
    
    def __init__(self, agent_id: str, current_state: str, required_state: str):
        super().__init__(
            f"Agent {agent_id} cannot transition from '{current_state}' to '{required_state}'",
            {
                "agent_id": agent_id,
                "current_state": current_state,
                "required_state": required_state
            }
        )


class CapabilityNotFoundError(OrchestratorError):
    """Raised when a requested capability is not found."""
    
    def __init__(self, capability_name: str):
        super().__init__(
            f"Capability not found: {capability_name}",
            {"capability_name": capability_name}
        )


class TaskNotFoundError(OrchestratorError):
    """Raised when a task is not found."""
    
    def __init__(self, task_id: str):
        super().__init__(
            f"Task not found: {task_id}",
            {"task_id": task_id}
        )


class InvalidTaskStateError(OrchestratorError):
    """Raised when a task is in an invalid state for the requested operation."""
    
    def __init__(self, task_id: str, current_state: str, required_state: str):
        super().__init__(
            f"Task {task_id} is in invalid state '{current_state}', required state: '{required_state}'",
            {
                "task_id": task_id,
                "current_state": current_state,
                "required_state": required_state
            }
        )


class AgentCapacityExceededError(OrchestratorError):
    """Raised when an agent exceeds its capacity limits."""
    
    def __init__(self, agent_id: str, current_load: int, max_capacity: int):
        super().__init__(
            f"Agent {agent_id} has exceeded capacity: {current_load}/{max_capacity}",
            {
                "agent_id": agent_id,
                "current_load": current_load,
                "max_capacity": max_capacity
            }
        )


class ConfigurationError(OrchestratorError):
    """Raised when there is a configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message,
            {"config_key": config_key} if config_key else {}
        )