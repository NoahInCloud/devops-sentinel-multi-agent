"""Agent-to-Agent (A2A) communication protocol for DevOps Sentinel."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Message types for A2A communication."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class A2AMessage:
    """Represents a message in the A2A protocol."""
    
    def __init__(
        self,
        message_type: MessageType,
        sender_id: str,
        recipient_id: str,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        self.id = str(uuid.uuid4())
        self.message_type = message_type
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.content = content
        self.priority = priority
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.expires_at = expires_at or (self.created_at + timedelta(minutes=30))
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create message from dictionary."""
        message = cls(
            message_type=MessageType(data["type"]),
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            content=data["content"],
            priority=MessagePriority(data["priority"]),
            correlation_id=data["correlation_id"],
            expires_at=datetime.fromisoformat(data["expires_at"])
        )
        message.id = data["id"]
        message.created_at = datetime.fromisoformat(data["created_at"])
        return message

class A2AProtocol:
    """Agent-to-Agent communication protocol."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.agents: Dict[str, Any] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
    async def start(self):
        """Start the A2A protocol."""
        self.running = True
        logger.info(f"A2A protocol started for agent {self.agent_id}")
        
        # Start message processing loop
        asyncio.create_task(self._process_messages())
        
    async def stop(self):
        """Stop the A2A protocol."""
        self.running = False
        logger.info(f"A2A protocol stopped for agent {self.agent_id}")
        
    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent for A2A communication."""
        self.agents[agent_id] = agent
        logger.info(f"Registered agent {agent_id}")
        
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self.message_handlers[message_type] = handler
        
    async def send_request(
        self,
        recipient_id: str,
        content: Dict[str, Any],
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Dict[str, Any]:
        """Send a request message and wait for response."""
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            content=content,
            priority=priority
        )
        
        # Create future for response
        response_future = asyncio.Future()
        self.pending_requests[message.correlation_id] = response_future
        
        try:
            await self._send_message(message)
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request to {recipient_id} timed out")
            raise
        finally:
            self.pending_requests.pop(message.correlation_id, None)
            
    async def send_response(
        self,
        recipient_id: str,
        content: Dict[str, Any],
        correlation_id: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """Send a response message."""
        message = A2AMessage(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            content=content,
            priority=priority,
            correlation_id=correlation_id
        )
        await self._send_message(message)
        
    async def send_notification(
        self,
        recipient_id: str,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """Send a notification message."""
        message = A2AMessage(
            message_type=MessageType.NOTIFICATION,
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            content=content,
            priority=priority
        )
        await self._send_message(message)
        
    async def broadcast(
        self,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """Broadcast message to all agents."""
        for agent_id in self.agents.keys():
            if agent_id != self.agent_id:
                await self.send_notification(agent_id, content, priority)
        
    async def _send_message(self, message: A2AMessage):
        """Send message to message queue for processing."""
        await self.message_queue.put(message)
        logger.debug(f"Queued {message.message_type.value} to {message.recipient_id}")
        
    async def _process_messages(self):
        """Process messages from the queue."""
        while self.running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self._deliver_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    async def _deliver_message(self, message: A2AMessage):
        """Deliver message to recipient agent."""
        try:
            # Check if message has expired
            if message.expires_at < datetime.utcnow():
                logger.warning(f"Message {message.id} has expired")
                return
                
            # Deliver to recipient agent
            if message.recipient_id in self.agents:
                recipient_agent = self.agents[message.recipient_id]
                
                # Call agent's message handler if it exists
                if hasattr(recipient_agent, 'handle_a2a_message'):
                    await recipient_agent.handle_a2a_message(message)
                else:
                    logger.warning(f"Agent {message.recipient_id} has no A2A message handler")
            else:
                logger.warning(f"Recipient agent {message.recipient_id} not found")
                
        except Exception as e:
            logger.error(f"Error delivering message: {e}")

    def get_agents(self) -> List[str]:
        """Get list of registered agent IDs."""
        return list(self.agents.keys())
        
    def get_agent_count(self) -> int:
        """Get number of registered agents."""
        return len(self.agents)