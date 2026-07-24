"""Agent Registry for the AI Agent Orchestrator."""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from .models import AgentInfo, AgentCapability
from .exceptions import AgentNotFoundError, AgentAlreadyExistsError


logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing agent registrations and lookups."""

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        self._lock = asyncio.Lock()

    async def register_agent(self, agent_info: AgentInfo) -> None:
        """Register an agent with the registry.
        
        Args:
            agent_info: Information about the agent to register
            
        Raises:
            AgentAlreadyExistsError: If an agent with the same ID is already registered
        """
        async with self._lock:
            if agent_info.id in self._agents:
                raise AgentAlreadyExistsError(agent_info.id)
            
            self._agents[agent_info.id] = agent_info
            
            # Update capability index
            for capability in agent_info.capabilities:
                cap_name = capability.name
                if cap_name not in self._capability_index:
                    self._capability_index[cap_name] = set()
                self._capability_index[cap_name].add(agent_info.id)
            
            logger.info(f"Registered agent: {agent_info.id}")

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Raises:
            AgentNotFoundError: If no agent with the given ID exists
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise AgentNotFoundError(agent_id)
            
            agent_info = self._agents[agent_id]
            
            # Remove from capability index
            for capability in agent_info.capabilities:
                cap_name = capability.name
                if cap_name in self._capability_index:
                    self._capability_index[cap_name].discard(agent_id)
                    if not self._capability_index[cap_name]:
                        del self._capability_index[cap_name]
            
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    async def update_agent(self, agent_info: AgentInfo) -> None:
        """Update an existing agent's information.
        
        Args:
            agent_info: Updated information for the agent
            
        Raises:
            AgentNotFoundError: If no agent with the given ID exists
        """
        async with self._lock:
            if agent_info.id not in self._agents:
                raise AgentNotFoundError(agent_info.id)
            
            # Remove old capability mappings
            old_agent = self._agents[agent_info.id]
            for capability in old_agent.capabilities:
                cap_name = capability.name
                if cap_name in self._capability_index:
                    self._capability_index[cap_name].discard(agent_info.id)
                    if not self._capability_index[cap_name]:
                        del self._capability_index[cap_name]
            
            # Update agent
            self._agents[agent_info.id] = agent_info
            
            # Add new capability mappings
            for capability in agent_info.capabilities:
                cap_name = capability.name
                if cap_name not in self._capability_index:
                    self._capability_index[cap_name] = set()
                self._capability_index[cap_name].add(agent_info.id)
            
            logger.info(f"Updated agent: {agent_info.id}")

    async def get_agent(self, agent_id: str) -> AgentInfo:
        """Get an agent by ID.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            AgentInfo: Information about the agent
            
        Raises:
            AgentNotFoundError: If no agent with the given ID exists
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise AgentNotFoundError(agent_id)
            return self._agents[agent_id]

    async def list_agents(self) -> List[AgentInfo]:
        """List all registered agents.
        
        Returns:
            List[AgentInfo]: List of all registered agents
        """
        async with self._lock:
            return list(self._agents.values())

    async def discover_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """Discover agents that have a specific capability.
        
        Args:
            capability: Name of the capability to search for
            
        Returns:
            List[AgentInfo]: List of agents that have the specified capability
        """
        async with self._lock:
            agent_ids = self._capability_index.get(capability, set())
            return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]

    async def discover_agents_by_capabilities(self, capabilities: List[str]) -> List[AgentInfo]:
        """Discover agents that have all of the specified capabilities.
        
        Args:
            capabilities: List of capability names to search for
            
        Returns:
            List[AgentInfo]: List of agents that have all specified capabilities
        """
        if not capabilities:
            return await self.list_agents()
        
        async with self._lock:
            # Start with agents that have the first capability
            if not capabilities:
                return await self.list_agents()
                
            agent_ids = self._capability_index.get(capabilities[0], set()).copy()
            
            # Intersect with agents that have each subsequent capability
            for capability in capabilities[1:]:
                if capability in self._capability_index:
                    agent_ids &= self._capability_index[capability]
                else:
                    # If no agent has this capability, return empty list
                    return []
            
            return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]

    async def get_agent_count(self) -> int:
        """Get the total number of registered agents.
        
        Returns:
            int: Number of registered agents
        """
        async with self._lock:
            return len(self._agents)

    async def clear(self) -> None:
        """Clear all registered agents."""
        async with self._lock:
            self._agents.clear()
            self._capability_index.clear()
            logger.info("Cleared all agents from registry")