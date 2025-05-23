"""Cost optimization agent for Azure resources."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import BaseDevOpsAgent, DevOpsAgentPlugin


class CostOptimizerPlugin(DevOpsAgentPlugin):
    """Plugin for cost optimization capabilities."""
    
    def __init__(self, subscription_id: str):
        super().__init__("cost_optimizer")
        self.subscription_id = subscription_id
        
    async def analyze_costs(self, time_period: str = "30d") -> str:
        """Analyze current cost patterns and identify optimization opportunities."""
        try:
            self.logger.info(f"Analyzing costs for subscription: {self.subscription_id}")
            
            # Mock cost data for demonstration
            current_costs = {
                'total_monthly_cost': 15000.00,
                'cost_by_service': {
                    'Virtual Machines': 8000.00,
                    'Storage': 2000.00,
                    'Networking': 1500.00,
                    'Databases': 2500.00,
                    'Other': 1000.00
                },
                'cost_by_region': {
                    'East US': 7000.00,
                    'West US': 5000.00,
                    'Europe': 3000.00
                },
                'cost_trend': 'increasing',
                'month_over_month_change': 12.5
            }
            
            optimization_opportunities = self._identify_optimization_opportunities(current_costs)
            
            result = f"Cost Analysis Report:\n\n"
            result += f"Current Monthly Cost: ${current_costs['total_monthly_cost']:,.2f}\n"
            result += f"Month-over-Month Change: {current_costs['month_over_month_change']:+.1f}%\n"
            result += f"Trend: {current_costs['cost_trend'].title()}\n\n"
            
            result += "Cost Breakdown by Service:\n"
            for service, cost in current_costs['cost_by_service'].items():
                percentage = (cost / current_costs['total_monthly_cost']) * 100
                result += f"- {service}: ${cost:,.2f} ({percentage:.1f}%)\n"
            
            result += "\nOptimization Opportunities:\n"
            total_savings = 0
            for i, opportunity in enumerate(optimization_opportunities, 1):
                result += f"{i}. {opportunity['title']}\n"
                result += f"   Potential Savings: ${opportunity['savings']:,.2f}/month\n"
                result += f"   Effort: {opportunity['effort']}\n"
                result += f"   Description: {opportunity['description']}\n\n"
                total_savings += opportunity['savings']
            
            result += f"Total Potential Monthly Savings: ${total_savings:,.2f}\n"
            result += f"Potential Annual Savings: ${total_savings * 12:,.2f}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing costs: {str(e)}")
            return f"Error analyzing costs: {str(e)}"
    
    async def get_rightsizing_recommendations(self) -> str:
        """Get recommendations for rightsizing Azure resources."""
        try:
            self.logger.info("Generating rightsizing recommendations")
            
            # Mock rightsizing data
            recommendations = [
                {
                    'resource_name': 'web-server-vm-01',
                    'resource_type': 'Virtual Machine',
                    'current_size': 'Standard_D4s_v3',
                    'recommended_size': 'Standard_D2s_v3',
                    'current_cost': 280.00,
                    'new_cost': 140.00,
                    'savings': 140.00,
                    'utilization': '25%',
                    'recommendation_reason': 'Low CPU and memory utilization'
                },
                {
                    'resource_name': 'database-server-01',
                    'resource_type': 'SQL Database',
                    'current_size': 'Standard S2',
                    'recommended_size': 'Standard S1',
                    'current_cost': 75.00,
                    'new_cost': 30.00,
                    'savings': 45.00,
                    'utilization': '35%',
                    'recommendation_reason': 'Low DTU utilization'
                }
            ]
            
            result = "Rightsizing Recommendations:\n\n"
            total_savings = 0
            
            for i, rec in enumerate(recommendations, 1):
                result += f"{i}. {rec['resource_name']} ({rec['resource_type']})\n"
                result += f"   Current: {rec['current_size']} (${rec['current_cost']:.2f}/month)\n"
                result += f"   Recommended: {rec['recommended_size']} (${rec['new_cost']:.2f}/month)\n"
                result += f"   Monthly Savings: ${rec['savings']:.2f}\n"
                result += f"   Current Utilization: {rec['utilization']}\n"
                result += f"   Reason: {rec['recommendation_reason']}\n\n"
                total_savings += rec['savings']
            
            result += f"Total Monthly Savings from Rightsizing: ${total_savings:.2f}\n"
            result += f"Total Annual Savings: ${total_savings * 12:.2f}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting rightsizing recommendations: {str(e)}")
            return f"Error getting rightsizing recommendations: {str(e)}"
    
    async def identify_unused_resources(self) -> str:
        """Identify unused or idle resources that can be removed."""
        try:
            self.logger.info("Identifying unused resources")
            
            # Mock unused resources data
            unused_resources = [
                {
                    'name': 'dev-storage-account-old',
                    'type': 'Storage Account',
                    'last_accessed': '60+ days ago',
                    'monthly_cost': 25.00,
                    'recommendation': 'Delete - No recent access'
                },
                {
                    'name': 'test-vm-abandoned',
                    'type': 'Virtual Machine',
                    'last_accessed': '30+ days ago',
                    'monthly_cost': 150.00,
                    'recommendation': 'Delete - Test environment no longer needed'
                },
                {
                    'name': 'backup-disk-orphaned',
                    'type': 'Managed Disk',
                    'last_accessed': 'Never attached',
                    'monthly_cost': 40.00,
                    'recommendation': 'Delete - Orphaned disk'
                }
            ]
            
            result = "Unused Resources Report:\n\n"
            total_waste = 0
            
            for i, resource in enumerate(unused_resources, 1):
                result += f"{i}. {resource['name']} ({resource['type']})\n"
                result += f"   Last Accessed: {resource['last_accessed']}\n"
                result += f"   Monthly Cost: ${resource['monthly_cost']:.2f}\n"
                result += f"   Recommendation: {resource['recommendation']}\n\n"
                total_waste += resource['monthly_cost']
            
            result += f"Total Monthly Waste: ${total_waste:.2f}\n"
            result += f"Total Annual Waste: ${total_waste * 12:.2f}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error identifying unused resources: {str(e)}")
            return f"Error identifying unused resources: {str(e)}"
    
    def _identify_optimization_opportunities(self, cost_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify cost optimization opportunities based on cost data."""
        opportunities = []
        
        # VM rightsizing opportunity
        vm_cost = cost_data['cost_by_service'].get('Virtual Machines', 0)
        if vm_cost > 5000:
            opportunities.append({
                'title': 'Virtual Machine Rightsizing',
                'savings': vm_cost * 0.25,  # 25% potential savings
                'effort': 'Medium',
                'description': 'Review VM sizes and rightsize based on actual utilization'
            })
        
        # Storage optimization
        storage_cost = cost_data['cost_by_service'].get('Storage', 0)
        if storage_cost > 1000:
            opportunities.append({
                'title': 'Storage Tier Optimization',
                'savings': storage_cost * 0.30,  # 30% potential savings
                'effort': 'Low',
                'description': 'Move infrequently accessed data to cool/archive tiers'
            })
        
        # Reserved instances
        if vm_cost > 3000:
            opportunities.append({
                'title': 'Reserved Instance Purchase',
                'savings': vm_cost * 0.40,  # 40% potential savings
                'effort': 'Low',
                'description': 'Purchase 1-year or 3-year reserved instances for stable workloads'
            })
        
        # Unused resources cleanup
        opportunities.append({
            'title': 'Unused Resources Cleanup',
            'savings': 500.00,  # Fixed potential savings
            'effort': 'Low',
            'description': 'Remove orphaned disks, unused storage accounts, and idle VMs'
        })
        
        return opportunities


class CostOptimizerAgent(BaseDevOpsAgent):
    """Agent responsible for Azure cost optimization."""
    
    def __init__(self, subscription_id: str):
        super().__init__("CostOptimizer", "Optimizes Azure costs and identifies savings opportunities")
        self.subscription_id = subscription_id
        self.capabilities = [
            "cost_analysis",
            "rightsizing_recommendations",
            "unused_resource_identification",
            "cost_forecasting"
        ]
        
    async def _setup_plugins(self):
        """Setup cost optimization plugins."""
        self.cost_plugin = CostOptimizerPlugin(self.subscription_id)
        self.kernel.add_plugin(
            plugin=self.cost_plugin,
            plugin_name="cost_optimizer",
            description="Cost optimization capabilities"
        )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process cost optimization requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'analyze_costs':
                time_period = params.get('time_period', '30d')
                result = await self.cost_plugin.analyze_costs(time_period)
            elif action == 'rightsizing_recommendations':
                result = await self.cost_plugin.get_rightsizing_recommendations()
            elif action == 'identify_unused':
                result = await self.cost_plugin.identify_unused_resources()
            else:
                result = f"Unknown action: {action}"
                
            return {
                'agent': self.name,
                'action': action,
                'status': 'success',
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {
                'agent': self.name,
                'action': action,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }