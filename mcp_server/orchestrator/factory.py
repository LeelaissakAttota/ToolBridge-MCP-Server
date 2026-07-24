"""Agent Factory for the AI Agent Orchestrator."""

import asyncio
import logging
from typing import Dict, Type, Any, Optional, Callable, Awaitable
from .models import AgentInfo, AgentCapability, AgentMetadata
from .exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating agent instances with dependency injection."""

    def __init__(self):
        self._agent_classes: Dict[str, Type] = {}
        self._dependencies: Dict[str, Any] = {}
        self._initializers: Dict[str, Callable[[], Awaitable[Any]]] = {}

    def register_agent_class(self, agent_type: str, agent_class: Type) -> None:
        """Register an agent class for the given type.
        
        Args:
            agent_type: Identifier for the agent type
            agent_class: Class to instantiate for this agent type
        """
        self._agent_classes[agent_type] = agent_class
        logger.debug(f"Registered agent class for type: {agent_type}")

    def unregister_agent_class(self, agent_type: str) -> None:
        """Unregister an agent class.
        
        Args:
            agent_type: Identifier for the agent type to remove
        """
        if agent_type in self._agent_classes:
            del self._agent_classes[agent_type]
            logger.debug(f"Unregistered agent class for type: {agent_type}")

    def register_dependency(self, name: str, dependency: Any) -> None:
        """Register a dependency that can be injected into agents.
        
        Args:
            name: Name identifier for the dependency
            dependency: The dependency object to inject
        """
        self._dependencies[name] = dependency
        logger.debug(f"Registered dependency: {name}")

    def register_initializer(self, name: str, initializer: Callable[[], Awaitable[Any]]) -> None:
        """Register an async initializer for dependencies.
        
        Args:
            name: Name identifier for the dependency
            initializer: Async function that returns the dependency
        """
        self._initializers[name] = initializer
        logger.debug(f"Registered initializer for: {name}")

    async def initialize_dependencies(self) -> None:
        """Initialize all registered async dependencies."""
        for name, initializer in self._initializers.items():
            try:
                self._dependencies[name] = await initializer()
                logger.debug(f"Initialized dependency: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize dependency {name}: {e}")
                raise ConfigurationError(f"Failed to initialize dependency {name}: {e}")

    def is_agent_type_registered(self, agent_type: str) -> bool:
        """Check if an agent type is registered.
        
        Args:
            agent_type: Identifier for the agent type
            
        Returns:
            bool: True if the agent type is registered
        """
        return agent_type in self._agent_classes

    def get_registered_agent_types(self) -> list[str]:
        """Get list of all registered agent types.
        
        Returns:
            List[str]: List of registered agent type identifiers
        """
        return list(self._agent_classes.keys())

    async def create_agent(
        self, 
        agent_type: str, 
        agent_id: str,
        name: str,
        description: str = "",
        capabilities: Optional[list] = None,
        configuration: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> AgentInfo:
        """Create an agent instance with dependency injection.
        
        Args:
            agent_type: Type of agent to create
            agent_id: Unique identifier for the agent instance
            name: Human-readable name for the agent
            description: Description of what the agent does
            capabilities: List of capabilities the agent possesses
            configuration: Configuration specific to this agent instance
            metadata: Additional metadata for the agent
            
        Returns:
            AgentInfo: Information about the created agent
            
        Raises:
            ConfigurationError: If the agent type is not registered
        """
        if agent_type not in self._agent_classes:
            raise ConfigurationError(f"Agent type not registered: {agent_type}")
        
        # Get the agent class
        agent_class = self._agent_classes[agent_type]
        
        # Prepare dependencies for injection
        dependencies = self._dependencies.copy()
        
        # Create agent instance
        try:
            # Try to instantiate with dependencies first
            agent_instance = agent_class(
                agent_id=agent_id,
                name=name,
                description=description,
                capabilities=capabilities or [],
                configuration=configuration or {},
                metadata=metadata or {},
                **dependencies
            )
        except TypeError:
            # Fallback to instantiation without dependencies if constructor doesn't accept them
            try:
                agent_instance = agent_class(
                    agent_id=agent_id,
                    name=name,
                    description=description,
                    capabilities=capabilities or [],
                    configuration=configuration or {},
                    metadata=metadata or {}
                )
                # Attach dependencies as attributes if the agent has a set_dependencies method
                if hasattr(agent_instance, 'set_dependencies'):
                    agent_instance.set_dependencies(dependencies)
            except Exception as e:
                raise ConfigurationError(f"Failed to instantiate agent {agent_type}: {e}")
        
        # Create AgentInfo
        agent_info = AgentInfo(
            id=agent_id,
            name=name,
            description=description,
            capabilities=[AgentCapability(name=cap.name, description=cap.description) 
                         for cap in (capabilities or [])],
            metadata=AgentMetadata(
                version=metadata.get("version", "1.0.0") if metadata else "1.0.0",
                author=metadata.get("author", "") if metadata else "",
                tags=metadata.get("tags", []) if metadata else [],
                configuration=configuration or {}
            )
        )
        
        logger.info(f"Created agent: {agent_id} of type {agent_type}")
        return agent_info

    async def create_agent_from_config(self, config: dict) -> AgentInfo:
        """Create an agent from a configuration dictionary.
        
        Args:
            config: Configuration dictionary containing:
                - type: Agent type (required)
                - id: Agent ID (required)
                - name: Agent name (required)
                - description: Agent description (optional)
                - capabilities: List of capability dicts (optional)
                - configuration: Agent configuration (optional)
                - metadata: Agent metadata (optional)
                
        Returns:
            AgentInfo: Information about the created agent
        """
        agent_type = config.get("type")
        agent_id = config.get("id")
        name = config.get("name")
        
        if not all([agent_type, agent_id, name]):
            raise ConfigurationError("Agent type, id, and name are required in config")
        
        capabilities = config.get("capabilities", [])
        description = config.get("description", "")
        configuration = config.get("configuration", {})
        metadata = config.get("metadata", {})
        
        return await self.create_agent(
            agent_type=agent_type,
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            configuration=configuration,
            metadata=metadata
        )