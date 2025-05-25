"""Core orchestrator for managing all DevOps agents."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from agents.infrastructure_monitor import InfrastructureMonitorAgent
from agents.rca_analyzer import RCAAnalyzerAgent
from agents.cost_optimizer import CostOptimizerAgent
from agents.deployment_manager import DeploymentManagerAgent
from agents.report_generator import ReportGeneratorAgent
from agents.kubernetes_agent import KubernetesAgent
from communication.a2a_protocol import A2AProtocol
from utils.azure_client import get_azure_client_manager


class DevOpsOrchestrator:
    """Main orchestrator for the DevOps multi-agent system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("orchestrator")
        self.agents: Dict[str, Any] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        self.a2a_protocol = A2AProtocol("orchestrator")
        self.azure_client_manager = None
        
    async def initialize(self):
        """Initialize all agents and start the orchestrator."""
        try:
            self.logger.info("Initializing DevOps Orchestrator...")
            
            # Initialize Azure client manager
            subscription_id = self.config.get('azure', {}).get('subscription_id')
            if subscription_id:
                self.azure_client_manager = get_azure_client_manager(subscription_id)
                
                # Validate Azure connection
                if await self.azure_client_manager.validate_connection():
                    self.logger.info("Successfully connected to Azure")
                else:
                    self.logger.warning("Could not validate Azure connection. Some features may be limited.")
            else:
                self.logger.warning("No Azure subscription ID configured. Running in limited mode.")
            
            # Start A2A protocol
            await self.a2a_protocol.start()
            
            # Initialize agents based on configuration
            await self._initialize_agents()
            
            # Register agents with A2A protocol
            for agent_name, agent in self.agents.items():
                self.a2a_protocol.register_agent(agent_name, agent)
            
            # Start agent monitoring
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._monitor_agents())
            
            self.logger.info("DevOps Orchestrator initialized successfully")
            self.logger.info(f"Active agents: {list(self.agents.keys())}")
            
        except Exception as e:
            self.logger.error(f"Error initializing orchestrator: {str(e)}", exc_info=True)
            raise
    
    async def _initialize_agents(self):
        """Initialize all DevOps agents."""
        subscription_id = self.config.get('azure', {}).get('subscription_id', '')
        kubernetes_config = self.config.get('kubernetes', {})
        agents_config = self.config.get('agents', {})
        
        # Check which agents are enabled
        enabled_agents = {
            agent['name']: agent 
            for agent in agents_config.get('agents', []) 
            if agent.get('enabled', True)
        }
        
        # Default to all agents if no config
        if not enabled_agents:
            enabled_agents = {
                'InfrastructureMonitor': {'enabled': True},
                'RCAAnalyzer': {'enabled': True},
                'CostOptimizer': {'enabled': True},
                'DeploymentManager': {'enabled': True},
                'ReportGenerator': {'enabled': True},
                'KubernetesAgent': {'enabled': True}
            }
        
        # Initialize enabled agents
        if 'InfrastructureMonitor' in enabled_agents:
            try:
                self.agents['infrastructure'] = InfrastructureMonitorAgent(subscription_id)
                await self.agents['infrastructure'].initialize()
                self.logger.info("Initialized Infrastructure Monitor Agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize Infrastructure Monitor: {str(e)}")
        
        if 'RCAAnalyzer' in enabled_agents:
            try:
                self.agents['rca'] = RCAAnalyzerAgent(subscription_id)
                await self.agents['rca'].initialize()
                self.logger.info("Initialized RCA Analyzer Agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize RCA Analyzer: {str(e)}")
        
        if 'CostOptimizer' in enabled_agents:
            try:
                self.agents['cost'] = CostOptimizerAgent(subscription_id)
                await self.agents['cost'].initialize()
                self.logger.info("Initialized Cost Optimizer Agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize Cost Optimizer: {str(e)}")
        
        if 'DeploymentManager' in enabled_agents:
            try:
                self.agents['deployment'] = DeploymentManagerAgent(subscription_id)
                await self.agents['deployment'].initialize()
                self.logger.info("Initialized Deployment Manager Agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize Deployment Manager: {str(e)}")
        
        if 'ReportGenerator' in enabled_agents:
            try:
                self.agents['report'] = ReportGeneratorAgent()
                await self.agents['report'].initialize()
                self.logger.info("Initialized Report Generator Agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize Report Generator: {str(e)}")
        
        if 'KubernetesAgent' in enabled_agents:
            try:
                # Merge Kubernetes config with kagent settings
                k8s_config = {
                    **kubernetes_config,
                    'kagent_endpoint': kubernetes_config.get('kagent', {}).get('api', {}).get('endpoint', 'http://kagent-service:8080')
                }
                self.agents['kubernetes'] = KubernetesAgent(k8s_config)
                await self.agents['kubernetes'].initialize()
                self.logger.info("Initialized Kubernetes Agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize Kubernetes Agent: {str(e)}")
        
        self.logger.info(f"Successfully initialized {len(self.agents)} agents")
    
    async def _monitor_agents(self):
        """Monitor agent health and performance."""
        while self.is_running:
            try:
                # Check agent status every 30 seconds
                await asyncio.sleep(30)
                
                for agent_name, agent in self.agents.items():
                    if not agent.is_active:
                        self.logger.warning(f"Agent {agent_name} is inactive")
                        # Attempt to restart agent
                        try:
                            await agent.initialize()
                            self.logger.info(f"Restarted agent {agent_name}")
                        except Exception as e:
                            self.logger.error(f"Failed to restart agent {agent_name}: {str(e)}")
                            
            except Exception as e:
                self.logger.error(f"Error in agent monitoring: {str(e)}")
    
    async def process_user_request(self, user_request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a user request and coordinate agent responses."""
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Processing user request {request_id}: {user_request[:100]}...")
            
            # Store active task
            self.active_tasks[request_id] = {
                'request': user_request,
                'start_time': start_time,
                'status': 'processing'
            }
            
            # Analyze the request to determine which agents to involve
            agent_plan = await self._analyze_request(user_request, context or {})
            
            if not agent_plan:
                # If no specific plan, provide general status
                agent_plan = {
                    'infrastructure': {'action': 'check_health', 'parameters': {}},
                    'cost': {'action': 'analyze_costs', 'parameters': {'time_period': '7d'}}
                }
            
            # Execute the plan
            results = await self._execute_agent_plan(agent_plan, request_id)
            
            # Compile final response
            response = await self._compile_response(results, user_request)
            
            # Update task status
            self.active_tasks[request_id]['status'] = 'completed'
            self.active_tasks[request_id]['end_time'] = datetime.utcnow()
            
            return {
                'request_id': request_id,
                'status': 'completed',
                'response': response,
                'agents_involved': list(agent_plan.keys()),
                'execution_time': (datetime.utcnow() - start_time).total_seconds(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing user request: {str(e)}", exc_info=True)
            
            # Update task status
            if request_id in self.active_tasks:
                self.active_tasks[request_id]['status'] = 'failed'
                self.active_tasks[request_id]['error'] = str(e)
            
            return {
                'request_id': request_id,
                'status': 'error',
                'error': str(e),
                'response': f"I encountered an error while processing your request: {str(e)}\n\nPlease try rephrasing your request or check the system logs for more details.",
                'timestamp': datetime.utcnow().isoformat()
            }
        finally:
            # Clean up old tasks
            self._cleanup_old_tasks()
    
    async def _analyze_request(self, user_request: str, context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze user request and create execution plan."""
        request_lower = user_request.lower()
        plan = {}
        
        # Infrastructure monitoring keywords
        if any(keyword in request_lower for keyword in ['health', 'monitor', 'status', 'uptime', 'performance', 'vm', 'virtual machine', 'resources']):
            plan['infrastructure'] = {
                'action': 'check_health',
                'parameters': context.get('infrastructure', {})
            }
            
            # Specific VM metrics
            if 'vm' in request_lower or 'virtual machine' in request_lower:
                plan['infrastructure']['action'] = 'get_vm_metrics'
                if 'metrics' in request_lower:
                    plan['infrastructure']['parameters']['detailed'] = True
        
        # Cost optimization keywords
        if any(keyword in request_lower for keyword in ['cost', 'spend', 'money', 'optimize', 'savings', 'expensive', 'budget', 'billing']):
            action = 'analyze_costs'
            params = context.get('cost', {})
            
            # Specific cost actions
            if 'rightsize' in request_lower or 'rightsizing' in request_lower:
                action = 'rightsizing_recommendations'
            elif 'unused' in request_lower or 'idle' in request_lower:
                action = 'identify_unused'
            elif 'tag' in request_lower:
                action = 'cost_by_tag'
                params['tag_name'] = context.get('tag_name', 'Environment')
            
            plan['cost'] = {
                'action': action,
                'parameters': params
            }
        
        # Incident analysis keywords
        if any(keyword in request_lower for keyword in ['incident', 'problem', 'issue', 'outage', 'rca', 'root cause', 'error', 'failure', 'down']):
            plan['rca'] = {
                'action': 'analyze_incident',
                'parameters': {
                    'incident_data': context.get('incident', {
                        'title': f'User reported issue: {user_request}',
                        'description': user_request,
                        'type': 'user_reported',
                        'symptoms': self._extract_symptoms(user_request),
                        'affected_resources': context.get('affected_resources', [])
                    })
                }
            }
        
        # Deployment keywords
        if any(keyword in request_lower for keyword in ['deploy', 'deployment', 'release', 'rollback', 'arm template']):
            if 'status' in request_lower or 'list' in request_lower:
                action = 'list_deployments'
            elif 'validate' in request_lower:
                action = 'validate_template'
            elif 'cancel' in request_lower:
                action = 'cancel_deployment'
            else:
                action = 'create_deployment'
            
            plan['deployment'] = {
                'action': action,
                'parameters': context.get('deployment', {})
            }
        
        # Kubernetes keywords
        if any(keyword in request_lower for keyword in ['kubernetes', 'k8s', 'pod', 'cluster', 'scale', 'aks']):
            if 'scale' in request_lower:
                action = 'scale_deployment'
            elif 'logs' in request_lower:
                action = 'get_pod_logs'
            elif 'resource' in request_lower or 'usage' in request_lower:
                action = 'get_resource_usage'
            elif 'kagent' in request_lower:
                action = 'kagent_action'
            else:
                action = 'get_cluster_status'
            
            plan['kubernetes'] = {
                'action': action,
                'parameters': context.get('kubernetes', {})
            }
        
        # Report generation keywords
        if any(keyword in request_lower for keyword in ['report', 'summary', 'analytics', 'dashboard', 'overview']):
            report_type = 'executive'  # default
            
            if 'infrastructure' in request_lower:
                report_type = 'infrastructure'
            elif 'cost' in request_lower:
                report_type = 'cost'
            elif 'incident' in request_lower:
                report_type = 'incident'
            elif 'deployment' in request_lower:
                report_type = 'deployment'
            
            plan['report'] = {
                'action': 'generate_report',
                'parameters': {
                    'report_type': report_type,
                    'data': context.get('report_data', {}),
                    'time_period': context.get('time_period', '30d')
                }
            }
        
        # Alert keywords
        if 'alert' in request_lower:
            if 'infrastructure' not in plan:
                plan['infrastructure'] = {
                    'action': 'check_alerts',
                    'parameters': {}
                }
        
        return plan
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptoms from user text."""
        symptoms = []
        
        symptom_keywords = {
            'slow': 'Performance degradation',
            'error': 'Errors occurring',
            'down': 'Service unavailable',
            'timeout': 'Connection timeouts',
            'high cpu': 'High CPU usage',
            'memory': 'Memory issues',
            'disk': 'Disk space issues',
            'network': 'Network connectivity issues',
            '500': 'HTTP 500 errors',
            '503': 'Service unavailable errors',
            'crash': 'Application crashes',
            'restart': 'Unexpected restarts'
        }
        
        text_lower = text.lower()
        for keyword, symptom in symptom_keywords.items():
            if keyword in text_lower:
                symptoms.append(symptom)
        
        if not symptoms:
            symptoms.append('General system issue')
        
        return symptoms
    
    async def _execute_agent_plan(self, agent_plan: Dict[str, Dict[str, Any]], request_id: str) -> Dict[str, Any]:
        """Execute the agent plan concurrently."""
        results = {}
        tasks = []
        
        for agent_name, agent_config in agent_plan.items():
            if agent_name in self.agents:
                # Create task for agent execution
                task = asyncio.create_task(
                    self._execute_agent_task(agent_name, agent_config, request_id),
                    name=f"{agent_name}_{request_id}"
                )
                tasks.append((agent_name, task))
            else:
                self.logger.warning(f"Agent {agent_name} not available")
                results[agent_name] = {
                    'agent': agent_name,
                    'status': 'unavailable',
                    'error': f'Agent {agent_name} is not initialized',
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        # Wait for all tasks with timeout
        try:
            # Set timeout based on action complexity
            timeout = 60  # 60 seconds default
            
            done, pending = await asyncio.wait(
                [task for _, task in tasks],
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                self.logger.warning(f"Task {task.get_name()} timed out")
            
            # Collect results
            for agent_name, task in tasks:
                try:
                    if task in done:
                        results[agent_name] = await task
                    else:
                        results[agent_name] = {
                            'agent': agent_name,
                            'status': 'timeout',
                            'error': 'Agent task timed out',
                            'timestamp': datetime.utcnow().isoformat()
                        }
                except Exception as e:
                    self.logger.error(f"Error getting result from {agent_name}: {str(e)}")
                    results[agent_name] = {
                        'agent': agent_name,
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    }
        
        except Exception as e:
            self.logger.error(f"Error executing agent plan: {str(e)}")
        
        return results
    
    async def _execute_agent_task(self, agent_name: str, agent_config: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Execute a single agent task."""
        try:
            agent = self.agents[agent_name]
            self.logger.info(f"Executing {agent_name} with action: {agent_config.get('action')}")
            
            result = await agent.process_request(agent_config)
            
            # Add request tracking
            result['request_id'] = request_id
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in agent {agent_name}: {str(e)}", exc_info=True)
            return {
                'agent': agent_name,
                'action': agent_config.get('action'),
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _compile_response(self, results: Dict[str, Any], original_request: str) -> str:
        """Compile agent results into a coherent response."""
        response_parts = []
        
        # Add header
        response_parts.append("# DevOps Sentinel Analysis\n")
        response_parts.append(f"**Request**: {original_request}\n")
        response_parts.append(f"**Time**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        
        # Count successful vs failed agents
        successful = sum(1 for r in results.values() if r.get('status') == 'success')
        total = len(results)
        
        if successful == 0:
            response_parts.append("\n⚠️ **Warning**: All agents encountered issues. Results may be limited.\n")
        elif successful < total:
            response_parts.append(f"\n📊 **Status**: {successful}/{total} agents responded successfully.\n")
        
        # Sort results by agent importance
        agent_order = ['infrastructure', 'kubernetes', 'cost', 'deployment', 'rca', 'report']
        
        # Add results from each agent
        for agent_name in agent_order:
            if agent_name in results:
                result = results[agent_name]
                
                if result['status'] == 'success':
                    response_parts.append(f"\n## {result['agent']} Analysis\n")
                    response_parts.append(result['result'])
                    response_parts.append("\n")
                elif result['status'] == 'error':
                    response_parts.append(f"\n## {result['agent']} (Error)\n")
                    response_parts.append(f"❌ {result.get('error', 'Unknown error')}\n")
        
        # Add any remaining agents not in the ordered list
        for agent_name, result in results.items():
            if agent_name not in agent_order:
                if result['status'] == 'success':
                    response_parts.append(f"\n## {result['agent']} Analysis\n")
                    response_parts.append(result['result'])
                    response_parts.append("\n")
        
        # Add footer
        response_parts.append("\n---\n")
        response_parts.append(f"*Analysis completed by DevOps Sentinel Multi-Agent System*\n")
        response_parts.append(f"*{successful} agents contributed to this analysis*\n")
        
        return ''.join(response_parts)
    
    def _cleanup_old_tasks(self):
        """Clean up old completed tasks."""
        try:
            current_time = datetime.utcnow()
            tasks_to_remove = []
            
            for task_id, task_info in self.active_tasks.items():
                # Remove tasks older than 1 hour
                if (current_time - task_info['start_time']).total_seconds() > 3600:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.active_tasks[task_id]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up tasks: {str(e)}")
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        status = {
            'orchestrator_status': 'running' if self.is_running else 'stopped',
            'total_agents': len(self.agents),
            'active_tasks': len(self.active_tasks),
            'azure_connected': self.azure_client_manager is not None,
            'agents': {}
        }
        
        for agent_name, agent in self.agents.items():
            try:
                agent_status = await agent.get_agent_status()
                status['agents'][agent_name] = {
                    'name': agent.name,
                    'type': agent.agent_type,
                    'active': agent.is_active,
                    'capabilities': agent.capabilities,
                    'model': agent.model_config.get('model', 'unknown')
                }
            except Exception as e:
                status['agents'][agent_name] = {
                    'name': agent_name,
                    'active': False,
                    'error': str(e)
                }
        
        # Add task summary
        status['recent_tasks'] = []
        for task_id, task_info in list(self.active_tasks.items())[-5:]:  # Last 5 tasks
            status['recent_tasks'].append({
                'id': task_id,
                'request': task_info['request'][:50] + '...' if len(task_info['request']) > 50 else task_info['request'],
                'status': task_info['status'],
                'start_time': task_info['start_time'].isoformat()
            })
        
        return status
    
    async def shutdown(self):
        """Shutdown the orchestrator and all agents."""
        self.logger.info("Shutting down DevOps Orchestrator...")
        self.is_running = False
        
        # Stop A2A protocol
        await self.a2a_protocol.stop()
        
        # Shutdown all agents
        shutdown_tasks = []
        for agent_name, agent in self.agents.items():
            try:
                task = asyncio.create_task(agent.shutdown())
                shutdown_tasks.append((agent_name, task))
            except Exception as e:
                self.logger.error(f"Error creating shutdown task for agent {agent_name}: {str(e)}")
        
        # Wait for all agents to shutdown
        for agent_name, task in shutdown_tasks:
            try:
                await asyncio.wait_for(task, timeout=5.0)
                self.logger.info(f"Agent {agent_name} shut down successfully")
            except asyncio.TimeoutError:
                self.logger.warning(f"Agent {agent_name} shutdown timed out")
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent_name}: {str(e)}")
        
        self.logger.info("DevOps Orchestrator shutdown complete")