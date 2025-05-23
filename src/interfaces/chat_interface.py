"""Chat interface for DevOps Sentinel with audio integration."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from quart import Quart, request, websocket, jsonify
from ..core.orchestrator import DevOpsOrchestrator


class ChatInterface:
    """Web-based chat interface for DevOps Sentinel."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app = Quart(__name__)
        self.logger = logging.getLogger("chat_interface")
        self.orchestrator = None
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Setup routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup Quart routes for the chat interface."""
        
        @self.app.route("/")
        async def index():
            """Serve the main chat interface."""
            return await self._render_chat_interface()
        
        @self.app.route("/api/chat", methods=["POST"])
        async def chat_endpoint():
            """Handle chat messages."""
            try:
                data = await request.get_json()
                message = data.get('message', '')
                session_id = data.get('session_id', 'default')
                context = data.get('context', {})
                
                if not message:
                    return jsonify({'error': 'No message provided'}), 400
                
                # Process the message through the orchestrator
                response = await self.orchestrator.process_user_request(message, context)
                
                # Store in session history
                if session_id not in self.active_sessions:
                    self.active_sessions[session_id] = {'messages': []}
                
                self.active_sessions[session_id]['messages'].extend([
                    {'type': 'user', 'content': message, 'timestamp': datetime.utcnow().isoformat()},
                    {'type': 'assistant', 'content': response['response'], 'timestamp': datetime.utcnow().isoformat()}
                ])
                
                return jsonify({
                    'response': response['response'],
                    'request_id': response['request_id'],
                    'agents_involved': response.get('agents_involved', []),
                    'status': response['status']
                })
                
            except Exception as e:
                self.logger.error(f"Error processing chat request: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route("/api/status")
        async def status_endpoint():
            """Get system status."""
            try:
                status = await self.orchestrator.get_agent_status()
                return jsonify(status)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route("/api/sessions/<session_id>/history")
        async def get_session_history(session_id: str):
            """Get chat history for a session."""
            session = self.active_sessions.get(session_id, {'messages': []})
            return jsonify(session)
        
        @self.app.websocket("/ws/chat")
        async def websocket_chat():
            """WebSocket endpoint for real-time chat."""
            try:
                self.logger.info("WebSocket chat connection established")
                
                while True:
                    message = await websocket.receive()
                    data = json.loads(message)
                    
                    if data.get('type') == 'chat':
                        # Process chat message
                        response = await self.orchestrator.process_user_request(
                            data.get('message', ''),
                            data.get('context', {})
                        )
                        
                        await websocket.send(json.dumps({
                            'type': 'response',
                            'content': response['response'],
                            'request_id': response['request_id'],
                            'agents_involved': response.get('agents_involved', []),
                            'timestamp': datetime.utcnow().isoformat()
                        }))
                    
                    elif data.get('type') == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                        
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
    
    async def _render_chat_interface(self) -> str:
        """Render the HTML chat interface."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevOps Sentinel - Multi-Agent Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4CAF50;
        }
        
        .chat-container {
            flex: 1;
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 10px 10px 0 0;
            overflow: hidden;
        }
        
        .sidebar {
            width: 300px;
            background: rgba(0, 0, 0, 0.05);
            padding: 1rem;
            border-right: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        .agent-list {
            margin-bottom: 2rem;
        }
        
        .agent-item {
            padding: 0.75rem;
            margin: 0.5rem 0;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .agent-name {
            font-weight: 600;
            color: #333;
        }
        
        .agent-status {
            font-size: 0.8rem;
            color: #666;
        }
        
        .main-chat {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .messages {
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            max-height: calc(100vh - 200px);
        }
        
        .message {
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 12px;
            max-width: 80%;
        }
        
        .message.user {
            background: #667eea;
            color: white;
            margin-left: auto;
        }
        
        .message.assistant {
            background: #f1f3f4;
            color: #333;
            border: 1px solid #e0e0e0;
        }
        
        .message-header {
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
            opacity: 0.7;
        }
        
        .input-area {
            padding: 1rem;
            border-top: 1px solid #e0e0e0;
            background: white;
        }
        
        .input-container {
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        
        .message-input {
            flex: 1;
            padding: 0.75rem;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            outline: none;
            font-size: 1rem;
        }
        
        .message-input:focus {
            border-color: #667eea;
        }
        
        .send-btn {
            padding: 0.75rem 1.5rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
        }
        
        .send-btn:hover {
            background: #5a6fd8;
        }
        
        .send-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .audio-btn {
            padding: 0.75rem;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .audio-btn:hover {
            background: #45a049;
        }
        
        .quick-actions {
            margin-bottom: 1rem;
        }
        
        .quick-action {
            display: block;
            width: 100%;
            padding: 0.5rem;
            margin: 0.25rem 0;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            cursor: pointer;
            text-align: left;
            font-size: 0.9rem;
        }
        
        .quick-action:hover {
            background: #f5f5f5;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 DevOps Sentinel</h1>
        <div class="status-indicator">
            <div class="status-dot"></div>
            <span>System Online</span>
        </div>
    </div>
    
    <div class="chat-container">
        <div class="sidebar">
            <div class="quick-actions">
                <h3>Quick Actions</h3>
                <button class="quick-action" onclick="sendQuickMessage('Show infrastructure health')">
                    📊 Infrastructure Health
                </button>
                <button class="quick-action" onclick="sendQuickMessage('Analyze current costs')">
                    💰 Cost Analysis
                </button>
                <button class="quick-action" onclick="sendQuickMessage('Check Kubernetes cluster status')">
                    ☸️ Kubernetes Status
                </button>
                <button class="quick-action" onclick="sendQuickMessage('List recent deployments')">
                    🚀 Recent Deployments
                </button>
                <button class="quick-action" onclick="sendQuickMessage('Generate executive report')">
                    📋 Executive Report
                </button>
            </div>
            
            <div class="agent-list">
                <h3>Active Agents</h3>
                <div class="agent-item">
                    <div class="agent-name">Infrastructure Monitor</div>
                    <div class="agent-status">Monitoring Azure resources</div>
                </div>
                <div class="agent-item">
                    <div class="agent-name">Cost Optimizer</div>
                    <div class="agent-status">Analyzing costs</div>
                </div>
                <div class="agent-item">
                    <div class="agent-name">RCA Analyzer</div>
                    <div class="agent-status">Ready for incidents</div>
                </div>
                <div class="agent-item">
                    <div class="agent-name">Deployment Manager</div>
                    <div class="agent-status">Managing deployments</div>
                </div>
                <div class="agent-item">
                    <div class="agent-name">Kubernetes Agent</div>
                    <div class="agent-status">Cluster management</div>
                </div>
                <div class="agent-item">
                    <div class="agent-name">Report Generator</div>
                    <div class="agent-status">Creating analytics</div>
                </div>
            </div>
        </div>
        
        <div class="main-chat">
            <div class="messages" id="messages">
                <div class="message assistant">
                    <div class="message-header">DevOps Sentinel • Just now</div>
                    <div>Welcome to DevOps Sentinel! I'm your multi-agent assistant for Azure DevOps operations. 
                    
I can help you with:
• Infrastructure monitoring and health checks
• Cost analysis and optimization
• Incident analysis and root cause investigation  
• Deployment management and rollbacks
• Kubernetes cluster operations
• Comprehensive reporting and analytics

What would you like me to help you with today?</div>
                </div>
            </div>
            
            <div class="input-area">
                <div class="input-container">
                    <input type="text" id="messageInput" class="message-input" 
                           placeholder="Ask me about your infrastructure, costs, deployments, or any DevOps questions..." 
                           onkeypress="handleKeyPress(event)">
                    <button class="audio-btn" onclick="toggleAudio()" title="Voice Input">
                        🎤
                    </button>
                    <button class="send-btn" onclick="sendMessage()" id="sendBtn">Send</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let socket;
        let isRecording = false;
        
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
            
            socket.onopen = function() {
                console.log('WebSocket connected');
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'response') {
                    addMessage('assistant', data.content, data.agents_involved);
                }
            };
            
            socket.onclose = function() {
                console.log('WebSocket disconnected');
                setTimeout(initWebSocket, 3000); // Reconnect after 3 seconds
            };
        }
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            
            // Send via WebSocket if available, otherwise fallback to HTTP
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'chat',
                    message: message,
                    context: {}
                }));
            } else {
                sendMessageHTTP(message);
            }
        }
        
        async function sendMessageHTTP(message) {
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: 'web_session',
                        context: {}
                    })
                });
                
                const data = await response.json();
                if (data.response) {
                    addMessage('assistant', data.response, data.agents_involved);
                } else if (data.error) {
                    addMessage('assistant', `Error: ${data.error}`);
                }
            } catch (error) {
                addMessage('assistant', `Error: ${error.message}`);
            }
        }
        
        function addMessage(type, content, agents = []) {
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            const timestamp = new Date().toLocaleTimeString();
            const sender = type === 'user' ? 'You' : 'DevOps Sentinel';
            const agentInfo = agents && agents.length > 0 ? ` • Agents: ${agents.join(', ')}` : '';
            
            messageDiv.innerHTML = `
                <div class="message-header">${sender} • ${timestamp}${agentInfo}</div>
                <div>${content.replace(/\\n/g, '<br>')}</div>
            `;
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }
        
        function sendQuickMessage(message) {
            document.getElementById('messageInput').value = message;
            sendMessage();
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        function toggleAudio() {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        }
        
        function startRecording() {
            // Audio recording implementation would go here
            // For now, just show a placeholder
            addMessage('assistant', 'Audio input feature coming soon! Please use text input for now.');
        }
        
        function stopRecording() {
            isRecording = false;
        }
        
        // Initialize WebSocket connection
        initWebSocket();
        
        // Focus input on load
        document.getElementById('messageInput').focus();
    </script>
</body>
</html>
        """
        return html
    
    async def initialize(self, orchestrator: DevOpsOrchestrator):
        """Initialize the chat interface with orchestrator."""
        self.orchestrator = orchestrator
        self.logger.info("Chat interface initialized")
    
    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """Run the chat interface server."""
        self.logger.info(f"Starting chat interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)