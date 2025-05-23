"""Core orchestrator for managing all DevOps agents."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from ..agents.infrastructure_monitor import InfrastructureMonitorAgent
from ..agents.rca_analyzer import RCAAnalyzerAgent
from ..agents.cost_optimizer import CostOptimizerAgent
from ..agents.deployment_manager import DeploymentManagerAgent
from ..agents.report_generator import ReportGeneratorAgent
from ..agents.kubernetes_agent import KubernetesAgent


class DevOpsOrchestrator:
    """Main orchestrator for the DevOps multi-agent system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("orchestrator")
        self.agents: Dict[str, Any] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        
    async def initialize(self):
        """Initialize all agents and start the orchestrator."""
        try:
            self.logger.info("Initializing DevOps Orchestrator...")
            
            # Initialize agents based on configuration
            await self._initialize_agents()
            
            # Start agent monitoring
            self.is_running = True
            self.logger.info("DevOps Orchestrator initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing orchestrator: {str(e)}")
            raise
    
    async def _initialize_agents(self):
        """Initialize all DevOps agents."""
        subscription_id = self.config.get('azure', {}).get('subscription_id', 'default-subscription')
        cluster_config = self.config.get('kubernetes', {})
        
        # Infrastructure Monitor Agent
        self.agents['infrastructure'] = InfrastructureMonitorAgent(subscription_id)
        await self.agents['infrastructure'].initialize()
        
        # RCA Analyzer Agent
        self.agents['rca'] = RCAAnalyzerAgent()
        await self.agents['rca'].initialize()
        
        # Cost Optimizer Agent
        self.agents['cost'] = CostOptimizerAgent(subscription_id)
        await self.agents['cost'].initialize()
        
        # Deployment Manager Agent
        self.agents['deployment'] = DeploymentManagerAgent(subscription_id)
        await self.agents['deployment'].initialize()
        
        # Report Generator Agent
        self.agents['report'] = ReportGeneratorAgent()
        await self.agents['report'].initialize()
        
        # Kubernetes Agent
        self.agents['kubernetes'] = KubernetesAgent(cluster_config)
        await self.agents['kubernetes'].initialize()
        
        self.logger.info(f"Initialized {len(self.agents)} agents")
    
    async def process_user_request(self, user_request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a user request and coordinate agent responses."""
        try:
            request_id = str(uuid.uuid4())
            self.logger.info(f"Processing user request {request_id}: {user_request}")
            
            # Analyze the request to determine which agents to involve
            agent_plan = await self._analyze_request(user_request, context or {})
            
            # Execute the plan
            results = await self._execute_agent_plan(agent_plan, request_id)
            
            # Compile final response
            response = await self._compile_response(results, user_request)
            
            return {
                'request_id': request_id,
                'status': 'completed',
                'response': response,
                'agents_involved': list(agent_plan.keys()),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing user request: {str(e)}")
            return {
                'request_id': request_id if 'request_id' in locals() else 'unknown',
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _analyze_request(self, user_request: str, context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze user request and create execution plan."""
        request_lower = user_request.lower()
        plan = {}
        
        # Infrastructure monitoring keywords
        if any(keyword in request_lower for keyword in ['health', 'monitor', 'status', 'uptime', 'performance']):
            plan['infrastructure'] = {
                'action': 'check_health',
                'parameters': context.get('infrastructure', {})
            }
        
        # Cost optimization keywords
        if any(keyword in request_lower for keyword in ['cost', 'spend', 'money', 'optimize', 'savings']):
            plan['cost'] = {
                'action': 'analyze_costs',
                'parameters': context.get('cost', {})
            }
        
        # Incident analysis keywords
        if any(keyword in request_lower for keyword in ['incident', 'problem', 'issue', 'outage', 'rca', 'root cause']):
            plan['rca'] = {
                'action': 'analyze_incident',
                'parameters': {
                    'incident_data': context.get('incident', {
                        'title': 'User reported incident',
                        'description': user_request,
                        'type': 'unknown',
                        'symptoms': [user_request],
                        'affected_resources': []
                    })
                }
            }
        
        # Deployment keywords
        if any(keyword in request_lower for keyword in ['deploy', 'deployment', 'release', 'rollback']):
            if 'rollback' in request_lower:
                plan['deployment'] = {
                    'action': 'rollback',
                    'parameters': context.get('deployment', {})
                }
            elif 'status' in request_lower or 'list' in request_lower:
                plan['deployment'] = {
                    'action': 'list_deployments',
                    'parameters': context.get('deployment', {})
                }
            else:
                plan['deployment'] = {
                    'action': 'create_deployment',
                    'parameters': context.get('deployment', {})
                }
        
        # Kubernetes keywords
        if any(keyword in request_lower for keyword in ['kubernetes', 'k8s', 'pod', 'cluster', 'scale']):
            if 'scale' in request_lower:
                plan['kubernetes'] = {
                    'action': 'scale_deployment',
                    'parameters': context.get('kubernetes', {})
                }
            elif 'logs' in request_lower:
                plan['kubernetes'] = {
                    'action': 'get_pod_logs',
                    'parameters': context.get('kubernetes', {})
                }
            else:
                plan['kubernetes'] = {
                    'action': 'get_cluster_status',
                    'parameters': context.get('kubernetes', {})
                }
        
        # Report generation keywords
        if any(keyword in request_lower for keyword in ['report', 'summary', 'analytics', 'dashboard']):
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
        
        # If no specific keywords found, provide general status
        if not plan:
            plan = {
                'infrastructure': {'action': 'check_health', 'parameters': {}},
                'cost': {'action': 'analyze_costs', 'parameters': {}},
                'kubernetes': {'action': 'get_cluster_status', 'parameters': {}}
            }
        
        return plan
    
    async def _execute_agent_plan(self, agent_plan: Dict[str, Dict[str, Any]], request_id: str) -> Dict[str, Any]:
        """Execute the agent plan concurrently."""
        results = {}
        tasks = []
        
        for agent_name, agent_config in agent_plan.items():
            if agent_name in self.agents:
                task = asyncio.create_task(
                    self.agents[agent_name].process_request(agent_config),
                    name=f"{agent_name}_{request_id}"
                )
                tasks.append((agent_name, task))
        
        # Wait for all tasks to complete
        for agent_name, task in tasks:
            try:
                result = await task
                results[agent_name] = result
            except Exception as e:
                self.logger.error(f"Error in agent {agent_name}: {str(e)}")
                results[agent_name] = {
                    'agent': agent_name,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return results
    
    async def _compile_response(self, results: Dict[str, Any], original_request: str) -> str:
        """Compile agent results into a coherent response."""
        response = f"DevOps Sentinel Response:\n\n"
        response += f"Original Request: {original_request}\n"
        response += f"Analysis completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        
        # Sort results by agent importance
        agent_order = ['infrastructure', 'kubernetes', 'cost', 'deployment', 'rca', 'report']
        
        for agent_name in agent_order:
            if agent_name in results:
                result = results[agent_name]
                if result['status'] == 'success':
                    response += f"📊 {result['agent']} Analysis:\n"
                    response += f"{result['result']}\n\n"
                else:
                    response += f"❌ {result['agent']} Error:\n"
                    response += f"{result.get('error', 'Unknown error')}\n\n"
        
        # Add any remaining agents not in the ordered list
        for agent_name, result in results.items():
            if agent_name not in agent_order:
                if result['status'] == 'success':
                    response += f"📊 {result['agent']} Analysis:\n"
                    response += f"{result['result']}\n\n"
                else:
                    response += f"❌ {result['agent']} Error:\n"
                    response += f"{result.get('error', 'Unknown error')}\n\n"
        
        response += "---\n"
        response += "DevOps Sentinel Multi-Agent System\n"
        response += f"Agents involved: {len(results)}\n"
        
        return response
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        status = {
            'orchestrator_status': 'running' if self.is_running else 'stopped',
            'total_agents': len(self.agents),
            'active_tasks': len(self.active_tasks),
            'agents': {}
        }
        
        for agent_name, agent in self.agents.items():
            status['agents'][agent_name] = {
                'name': agent.name,
                'active': agent.is_active,
                'capabilities': agent.capabilities
            }
        
        return status
    
    async def shutdown(self):
        """Shutdown the orchestrator and all agents."""
        self.logger.info("Shutting down DevOps Orchestrator...")
        self.is_running = False
        
        for agent_name, agent in self.agents.items():
            try:
                await agent.shutdown()
                self.logger.info(f"Agent {agent_name} shut down successfully")
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent_name}: {str(e)}")
        
        self.logger.info("DevOps Orchestrator shutdown complete")