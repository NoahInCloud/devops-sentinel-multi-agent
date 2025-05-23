"""WebSocket handler for real-time communication in DevOps Sentinel."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handles WebSocket connections for real-time communication."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.server = None
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler for a specific message type."""
        self.message_handlers[message_type] = handler
        
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on {host}:{port}")
        self.server = await websockets.serve(
            self.handle_client,
            host,
            port
        )
        return self.server
        
    async def stop_server(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
            
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new client connection."""
        client_id = str(uuid.uuid4())
        self.connections[client_id] = websocket
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            # Send welcome message
            await self.send_to_client(client_id, {
                "type": "welcome",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            async for message in websocket:
                await self.process_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            self.connections.pop(client_id, None)
            
    async def process_message(self, client_id: str, message: str):
        """Process incoming message from client."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            logger.debug(f"Received {message_type} message from client {client_id}")
            
            # Call registered handler if available
            if message_type in self.message_handlers:
                response = await self.message_handlers[message_type](client_id, data)
                if response:
                    await self.send_to_client(client_id, response)
            else:
                # Default echo response
                await self.send_to_client(client_id, {
                    "type": "echo",
                    "original_message": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message from client {client_id}: {message}")
            await self.send_error(client_id, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message from client {client_id}: {e}")
            await self.send_error(client_id, "Internal server error")
            
    async def send_to_client(self, client_id: str, data: Dict[str, Any]):
        """Send message to specific client."""
        if client_id in self.connections:
            try:
                message = json.dumps(data)
                await self.connections[client_id].send(message)
                logger.debug(f"Sent message to client {client_id}: {data.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
                
    async def broadcast(self, data: Dict[str, Any], exclude_client: Optional[str] = None):
        """Broadcast message to all connected clients."""
        message = json.dumps(data)
        disconnected_clients = []
        
        for client_id, websocket in self.connections.items():
            if exclude_client and client_id == exclude_client:
                continue
                
            try:
                await websocket.send(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)
                
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.connections.pop(client_id, None)
            
    async def send_error(self, client_id: str, error_message: str):
        """Send error message to client."""
        await self.send_to_client(client_id, {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IDs."""
        return list(self.connections.keys())
        
    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.connections)