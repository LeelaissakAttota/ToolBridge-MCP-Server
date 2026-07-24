"""Data models and enums for the AI Agent Orchestrator."""

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Status of a task."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY_READY = "retry_ready"


class TaskPriority(IntEnum):
    """Priority levels for tasks."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class AgentStatus(str, Enum):
    """Status of an agent."""
    CREATED = "created"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    BUSY = "busy"
    IDLE = "idle"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


class AgentCapability(BaseModel):
    """Capability that an agent can perform."""
    model_config = ConfigDict(frozen=True)
    
    name: str = Field(..., description="Unique name of the capability")
    description: str = Field("", description="Description of what the capability does")


class AgentMetadata(BaseModel):
    """Metadata about an agent."""
    model_config = ConfigDict(frozen=False)
    
    version: str = Field("1.0.0", description="Version of the agent")
    author: str = Field("", description="Author of the agent")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Agent-specific configuration")


class AgentInfo(BaseModel):
    """Information about a registered agent."""
    model_config = ConfigDict(frozen=False)
    
    id: str = Field(..., description="Unique identifier for the agent")
    name: str = Field(..., description="Human-readable name of the agent")
    description: str = Field("", description="Description of what the agent does")
    capabilities: list[AgentCapability] = Field(default_factory=list, description="List of capabilities")
    status: AgentStatus = Field(AgentStatus.CREATED, description="Current status of the agent")
    metadata: AgentMetadata = Field(default_factory=AgentMetadata, description="Additional metadata")
    
    # Runtime information
    current_task_id: Optional[str] = Field(None, description="ID of the task currently being processed")
    error_count: int = Field(0, description="Number of consecutive errors")
    last_heartbeat: Optional[float] = Field(None, description="Timestamp of last heartbeat")


class Task(BaseModel):
    """Task to be executed by an agent."""
    model_config = ConfigDict(frozen=False)
    
    id: str = Field(..., description="Unique identifier for the task")
    name: str = Field(..., description="Human-readable name of the task")
    description: str = Field("", description="Description of what the task does")
    capability_required: str = Field(..., description="Capability required to execute this task")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Priority level of the task")
    payload: dict[str, Any] = Field(default_factory=dict, description="Data required to execute the task")
    
    # Lifecycle
    status: TaskStatus = Field(TaskStatus.QUEUED, description="Current status of the task")
    assigned_agent_id: Optional[str] = Field(None, description="ID of the agent assigned to this task")
    result: Optional[Any] = Field(None, description="Result of the task execution")
    error: Optional[str] = Field(None, description="Error message if task failed")
    retry_count: int = Field(0, description="Number of times this task has been retried")
    max_retries: int = Field(3, description="Maximum number of retries allowed")


class TaskResult(BaseModel):
    """Result of a task execution."""
    model_config = ConfigDict(frozen=False)
    
    task_id: str = Field(..., description="ID of the task")
    agent_id: str = Field(..., description="ID of the agent that executed the task")
    success: bool = Field(..., description="Whether the task was successful")
    result: Any = Field(None, description="Result data from the task")
    error: Optional[str] = Field(None, description="Error message if task failed")
    execution_time: float = Field(0.0, description="Time taken to execute the task in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")