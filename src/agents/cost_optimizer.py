"""Cost optimization agent for Azure resources using real Azure Cost Management API."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure.mgmt.costmanagement.models import (
    QueryDefinition, QueryDataset, QueryAggregation, 
    QueryGrouping, QueryTimePeriod, TimeframeType,
    QueryFilter, QueryComparisonExpression, QueryOperatorType
)

from utils.azure_client import get_azure_client_manager
from agents.base_agent import BaseDevOpsAgent, DevOpsAgentPlugin
from semantic_kernel.functions import kernel_function


class CostOptimizerPlugin(DevOpsAgentPlugin):
    """Plugin for cost optimization capabilities."""
    
    def __init__(self, subscription_id: str):
        super().__init__("cost_optimizer")
        self.subscription_id = subscription_id
        self.azure_clients = get_azure_client_manager(subscription_id)
        
    @kernel_function(name="analyze_costs", description="Analyze current Azure costs and trends")
    async def analyze_costs(self, time_period: str = "30d") -> str:
        """Analyze current cost patterns using real Azure Cost Management data."""
        try:
            self.logger.info(f"Analyzing costs for subscription: {self.subscription_id}")
            
            cost_client = self.azure_clients.get_cost_client()
            scope = f"/subscriptions/{self.subscription_id}"
            
            # Determine timeframe
            if time_period == "7d":
                timeframe = TimeframeType.THE_LAST7_DAYS
            elif time_period == "30d":
                timeframe = TimeframeType.THE_LAST30_DAYS
            else:
                timeframe = TimeframeType.MONTH_TO_DATE
            
            # Query for total costs by service
            query_by_service = QueryDefinition(
                type="ActualCost",
                timeframe=timeframe,
                dataset=QueryDataset(
                    granularity="Daily",
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="Cost",
                            function="Sum"
                        )
                    },
                    grouping=[
                        QueryGrouping(
                            type="Dimension",
                            name="ServiceName"
                        )
                    ]
                )
            )
            
            # Execute query
            result_by_service = cost_client.query.usage(
                scope=scope,
                parameters=query_by_service
            )
            
            # Query for total costs by resource group
            query_by_rg = QueryDefinition(
                type="ActualCost",
                timeframe=timeframe,
                dataset=QueryDataset(
                    granularity="None",
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="Cost",
                            function="Sum"
                        )
                    },
                    grouping=[
                        QueryGrouping(
                            type="Dimension",
                            name="ResourceGroup"
                        )
                    ]
                )
            )
            
            result_by_rg = cost_client.query.usage(
                scope=scope,
                parameters=query_by_rg
            )
            
            # Process results
            total_cost = 0
            costs_by_service = {}
            
            if hasattr(result_by_service, 'rows'):
                for row in result_by_service.rows:
                    service_name = row[1] if len(row) > 1 else "Unknown"
                    cost = float(row[0]) if row[0] else 0
                    costs_by_service[service_name] = cost
                    total_cost += cost
            
            costs_by_rg = {}
            if hasattr(result_by_rg, 'rows'):
                for row in result_by_rg.rows:
                    rg_name = row[1] if len(row) > 1 else "Unknown"
                    cost = float(row[0]) if row[0] else 0
                    costs_by_rg[rg_name] = cost
            
            # Get previous period for comparison
            if timeframe == TimeframeType.THE_LAST7_DAYS:
                prev_start = datetime.utcnow() - timedelta(days=14)
                prev_end = datetime.utcnow() - timedelta(days=7)
            else:
                prev_start = datetime.utcnow() - timedelta(days=60)
                prev_end = datetime.utcnow() - timedelta(days=30)
            
            query_prev = QueryDefinition(
                type="ActualCost",
                timeframe=TimeframeType.CUSTOM,
                time_period=QueryTimePeriod(
                    from_property=prev_start,
                    to=prev_end
                ),
                dataset=QueryDataset(
                    granularity="None",
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="Cost",
                            function="Sum"
                        )
                    }
                )
            )
            
            result_prev = cost_client.query.usage(
                scope=scope,
                parameters=query_prev
            )
            
            prev_total = 0
            if hasattr(result_prev, 'rows') and result_prev.rows:
                prev_total = float(result_prev.rows[0][0]) if result_prev.rows[0][0] else 0
            
            # Calculate change
            if prev_total > 0:
                change_percentage = ((total_cost - prev_total) / prev_total) * 100
            else:
                change_percentage = 0
            
            # Format results
            result = f"Cost Analysis Report (Real Azure Data):\n\n"
            result += f"📊 Cost Summary ({time_period}):\n"
            result += f"• Total Cost: ${total_cost:,.2f}\n"
            result += f"• Previous Period: ${prev_total:,.2f}\n"
            result += f"• Change: {change_percentage:+.1f}%\n"
            result += f"• Daily Average: ${total_cost / 30:,.2f}\n"
            result += f"• Projected Monthly: ${(total_cost / 30) * 30:,.2f}\n\n"
            
            result += "💰 Top Services by Cost:\n"
            sorted_services = sorted(costs_by_service.items(), key=lambda x: x[1], reverse=True)
            for i, (service, cost) in enumerate(sorted_services[:10], 1):
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                result += f"{i}. {service}: ${cost:,.2f} ({percentage:.1f}%)\n"
            
            result += "\n📁 Top Resource Groups by Cost:\n"
            sorted_rgs = sorted(costs_by_rg.items(), key=lambda x: x[1], reverse=True)
            for i, (rg, cost) in enumerate(sorted_rgs[:5], 1):
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                result += f"{i}. {rg}: ${cost:,.2f} ({percentage:.1f}%)\n"
            
            # Get optimization opportunities
            opportunities = await self._analyze_optimization_opportunities(costs_by_service, total_cost)
            
            result += f"\n💡 Cost Optimization Opportunities:\n"
            total_savings = 0
            for opp in opportunities:
                result += f"• {opp['title']}: ${opp['savings']:,.2f}/month potential savings\n"
                result += f"  Action: {opp['action']}\n"
                total_savings += opp['savings']
            
            result += f"\n🎯 Total Potential Savings: ${total_savings:,.2f}/month (${total_savings * 12:,.2f}/year)\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing costs: {str(e)}")
            return f"Error analyzing costs: {str(e)}"
    
    @kernel_function(name="get_cost_by_tag", description="Analyze costs grouped by tags")
    async def get_cost_by_tag(self, tag_name: str = "Environment") -> str:
        """Get costs grouped by a specific tag."""
        try:
            cost_client = self.azure_clients.get_cost_client()
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = QueryDefinition(
                type="ActualCost",
                timeframe=TimeframeType.MONTH_TO_DATE,
                dataset=QueryDataset(
                    granularity="None",
                    aggregation={
                        "totalCost": QueryAggregation(
                            name="Cost",
                            function="Sum"
                        )
                    },
                    grouping=[
                        QueryGrouping(
                            type="Tag",
                            name=tag_name
                        )
                    ]
                )
            )
            
            result_data = cost_client.query.usage(
                scope=scope,
                parameters=query
            )
            
            result = f"Cost Analysis by Tag '{tag_name}':\n\n"
            
            total_cost = 0
            tag_costs = {}
            
            if hasattr(result_data, 'rows'):
                for row in result_data.rows:
                    tag_value = row[1] if len(row) > 1 else "Untagged"
                    cost = float(row[0]) if row[0] else 0
                    tag_costs[tag_value] = cost
                    total_cost += cost
            
            result += f"📊 Total Cost: ${total_cost:,.2f}\n\n"
            result += f"🏷️ Costs by {tag_name}:\n"
            
            sorted_tags = sorted(tag_costs.items(), key=lambda x: x[1], reverse=True)
            for tag_value, cost in sorted_tags:
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                result += f"• {tag_value}: ${cost:,.2f} ({percentage:.1f}%)\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting cost by tag: {str(e)}")
            return f"Error getting cost by tag: {str(e)}"
    
    @kernel_function(name="get_rightsizing_recommendations", description="Get VM rightsizing recommendations")
    async def get_rightsizing_recommendations(self) -> str:
        """Get recommendations for rightsizing Azure VMs based on actual usage."""
        try:
            self.logger.info("Generating rightsizing recommendations")
            
            compute_client = self.azure_clients.get_compute_client()
            monitor_client = self.azure_clients.get_monitor_client()
            
            recommendations = []
            total_current_cost = 0
            total_savings = 0
            
            # VM size pricing (simplified - in production, use Azure Pricing API)
            vm_pricing = {
                'Standard_D2s_v3': 96,
                'Standard_D4s_v3': 192,
                'Standard_D8s_v3': 384,
                'Standard_D16s_v3': 768,
                'Standard_E2s_v3': 126,
                'Standard_E4s_v3': 252,
                'Standard_E8s_v3': 504,
                'Standard_B1ms': 20,
                'Standard_B2ms': 80,
                'Standard_B4ms': 160
            }
            
            # Get all VMs
            vms = list(compute_client.virtual_machines.list_all())[:20]  # Limit for performance
            
            for vm in vms:
                try:
                    # Get resource group from ID
                    resource_group = vm.id.split('/')[4]
                    
                    # Get current size and estimated cost
                    current_size = vm.hardware_profile.vm_size
                    current_cost = vm_pricing.get(current_size, 200)  # Default cost if size not in list
                    total_current_cost += current_cost
                    
                    # Get CPU metrics for the last 7 days
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=7)
                    
                    metrics = monitor_client.metrics.list(
                        vm.id,
                        timespan=f"{start_time}/{end_time}",
                        interval='PT1H',
                        metricnames='Percentage CPU',
                        aggregation='Average,Maximum'
                    )
                    
                    # Analyze CPU usage
                    avg_cpu = 0
                    max_cpu = 0
                    data_points = 0
                    
                    for metric in metrics.value:
                        for timeseries in metric.timeseries:
                            for data in timeseries.data:
                                if data.average is not None:
                                    avg_cpu += data.average
                                    data_points += 1
                                if data.maximum is not None:
                                    max_cpu = max(max_cpu, data.maximum)
                    
                    if data_points > 0:
                        avg_cpu = avg_cpu / data_points
                    
                    # Determine if rightsizing is needed
                    if avg_cpu < 20 and max_cpu < 40:
                        # VM is underutilized - recommend smaller size
                        if current_size == 'Standard_D4s_v3':
                            new_size = 'Standard_D2s_v3'
                        elif current_size == 'Standard_D8s_v3':
                            new_size = 'Standard_D4s_v3'
                        elif current_size == 'Standard_D16s_v3':
                            new_size = 'Standard_D8s_v3'
                        elif current_size == 'Standard_E4s_v3':
                            new_size = 'Standard_E2s_v3'
                        elif current_size == 'Standard_E8s_v3':
                            new_size = 'Standard_E4s_v3'
                        else:
                            new_size = 'Standard_B2ms'  # Default smaller size
                        
                        new_cost = vm_pricing.get(new_size, 80)
                        savings = current_cost - new_cost
                        total_savings += savings
                        
                        recommendations.append({
                            'vm_name': vm.name,
                            'resource_group': resource_group,
                            'current_size': current_size,
                            'recommended_size': new_size,
                            'current_cost': current_cost,
                            'new_cost': new_cost,
                            'monthly_savings': savings,
                            'avg_cpu': avg_cpu,
                            'max_cpu': max_cpu,
                            'reason': f'Low CPU utilization (avg: {avg_cpu:.1f}%, max: {max_cpu:.1f}%)'
                        })
                    
                except Exception as e:
                    self.logger.warning(f"Could not analyze VM {vm.name}: {str(e)}")
                    continue
            
            # Format results
            result = f"VM Rightsizing Recommendations (Based on Real Usage Data):\n\n"
            result += f"📊 Analysis Summary:\n"
            result += f"• VMs Analyzed: {len(vms)}\n"
            result += f"• Rightsizing Opportunities: {len(recommendations)}\n"
            result += f"• Current Monthly Cost: ${total_current_cost:,.2f}\n"
            result += f"• Potential Monthly Savings: ${total_savings:,.2f}\n"
            result += f"• Potential Annual Savings: ${total_savings * 12:,.2f}\n\n"
            
            if recommendations:
                result += "💡 Rightsizing Recommendations:\n\n"
                for i, rec in enumerate(recommendations[:10], 1):
                    result += f"{i}. **{rec['vm_name']}** (RG: {rec['resource_group']})\n"
                    result += f"   Current: {rec['current_size']} (${rec['current_cost']}/month)\n"
                    result += f"   Recommended: {rec['recommended_size']} (${rec['new_cost']}/month)\n"
                    result += f"   Monthly Savings: ${rec['monthly_savings']}\n"
                    result += f"   Reason: {rec['reason']}\n\n"
                
                if len(recommendations) > 10:
                    result += f"... and {len(recommendations) - 10} more recommendations\n"
            else:
                result += "✅ No rightsizing opportunities found. VMs appear to be appropriately sized.\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting rightsizing recommendations: {str(e)}")
            return f"Error getting rightsizing recommendations: {str(e)}"
    
    @kernel_function(name="identify_unused_resources", description="Find unused or idle Azure resources")
    async def identify_unused_resources(self) -> str:
        """Identify unused or idle resources that can be removed."""
        try:
            self.logger.info("Identifying unused resources")
            
            unused_resources = []
            total_waste = 0
            
            # Check for unused disks
            compute_client = self.azure_clients.get_compute_client()
            disks = list(compute_client.disks.list())
            
            for disk in disks:
                if disk.disk_state == 'Unattached':
                    # Estimate cost based on disk size and type
                    disk_size_gb = disk.disk_size_gb or 0
                    if disk.sku.name == 'Premium_LRS':
                        cost_per_gb = 0.135  # Premium SSD
                    elif disk.sku.name == 'StandardSSD_LRS':
                        cost_per_gb = 0.075  # Standard SSD
                    else:
                        cost_per_gb = 0.04   # Standard HDD
                    
                    monthly_cost = disk_size_gb * cost_per_gb
                    total_waste += monthly_cost
                    
                    unused_resources.append({
                        'type': 'Managed Disk',
                        'name': disk.name,
                        'resource_group': disk.id.split('/')[4],
                        'details': f'{disk_size_gb} GB {disk.sku.name}',
                        'monthly_cost': monthly_cost,
                        'recommendation': 'Delete unattached disk'
                    })
            
            # Check for stopped VMs
            vms = list(compute_client.virtual_machines.list_all())
            for vm in vms:
                try:
                    resource_group = vm.id.split('/')[4]
                    instance_view = compute_client.virtual_machines.instance_view(
                        resource_group,
                        vm.name
                    )
                    
                    # Check if VM is deallocated but not removed
                    is_stopped = False
                    for status in instance_view.statuses:
                        if status.code == 'PowerState/deallocated':
                            is_stopped = True
                            break
                    
                    if is_stopped:
                        # Estimate VM cost
                        vm_size = vm.hardware_profile.vm_size
                        estimated_cost = 100  # Default estimate
                        
                        unused_resources.append({
                            'type': 'Virtual Machine',
                            'name': vm.name,
                            'resource_group': resource_group,
                            'details': f'Deallocated {vm_size}',
                            'monthly_cost': estimated_cost,
                            'recommendation': 'Delete if no longer needed'
                        })
                        total_waste += estimated_cost
                        
                except Exception as e:
                    continue
            
            # Check for unused public IPs
            network_client = self.azure_clients.get_network_client()
            public_ips = list(network_client.public_ip_addresses.list_all())
            
            for ip in public_ips:
                if not ip.ip_configuration:
                    # Unassociated public IP
                    monthly_cost = 3.65  # Approximate cost for static IP
                    total_waste += monthly_cost
                    
                    unused_resources.append({
                        'type': 'Public IP',
                        'name': ip.name,
                        'resource_group': ip.id.split('/')[4],
                        'details': f'{ip.public_ip_allocation_method} IP',
                        'monthly_cost': monthly_cost,
                        'recommendation': 'Delete unassociated IP'
                    })
            
            # Format results
            result = f"Unused Resources Report:\n\n"
            result += f"📊 Summary:\n"
            result += f"• Total Unused Resources: {len(unused_resources)}\n"
            result += f"• Total Monthly Waste: ${total_waste:,.2f}\n"
            result += f"• Total Annual Waste: ${total_waste * 12:,.2f}\n\n"
            
            if unused_resources:
                # Group by type
                by_type = {}
                for resource in unused_resources:
                    res_type = resource['type']
                    if res_type not in by_type:
                        by_type[res_type] = []
                    by_type[res_type].append(resource)
                
                result += "🗑️ Unused Resources by Type:\n\n"
                for res_type, resources in by_type.items():
                    type_cost = sum(r['monthly_cost'] for r in resources)
                    result += f"**{res_type}** ({len(resources)} items, ${type_cost:,.2f}/month):\n"
                    
                    for resource in resources[:5]:
                        result += f"• {resource['name']} ({resource['resource_group']})\n"
                        result += f"  Details: {resource['details']}\n"
                        result += f"  Cost: ${resource['monthly_cost']:,.2f}/month\n"
                        result += f"  Action: {resource['recommendation']}\n"
                    
                    if len(resources) > 5:
                        result += f"  ... and {len(resources) - 5} more\n"
                    result += "\n"
            else:
                result += "✅ No unused resources found. Good resource hygiene!\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error identifying unused resources: {str(e)}")
            return f"Error identifying unused resources: {str(e)}"
    
    async def _analyze_optimization_opportunities(self, costs_by_service: Dict[str, float], total_cost: float) -> List[Dict[str, Any]]:
        """Analyze cost data to identify optimization opportunities."""
        opportunities = []
        
        # VM optimization
        vm_cost = costs_by_service.get('Virtual Machines', 0)
        if vm_cost > total_cost * 0.2:  # VMs are >20% of costs
            opportunities.append({
                'title': 'Virtual Machine Optimization',
                'savings': vm_cost * 0.3,  # Estimate 30% savings
                'action': 'Review VM sizes, implement auto-shutdown, and consider Reserved Instances'
            })
        
        # Storage optimization
        storage_cost = sum(cost for service, cost in costs_by_service.items() 
                          if 'Storage' in service or 'Disk' in service)
        if storage_cost > total_cost * 0.1:  # Storage >10% of costs
            opportunities.append({
                'title': 'Storage Tier Optimization',
                'savings': storage_cost * 0.25,
                'action': 'Move cold data to Archive tier, delete old snapshots'
            })
        
        # Database optimization
        db_cost = sum(cost for service, cost in costs_by_service.items() 
                     if 'SQL' in service or 'Cosmos' in service or 'Database' in service)
        if db_cost > 0:
            opportunities.append({
                'title': 'Database Optimization',
                'savings': db_cost * 0.2,
                'action': 'Review DTU/vCore usage, consider elastic pools'
            })
        
        # General recommendations
        opportunities.append({
            'title': 'Implement Cost Alerts',
            'savings': total_cost * 0.05,  # 5% from better monitoring
            'action': 'Set up budget alerts and anomaly detection'
        })
        
        return opportunities


class CostOptimizerAgent(BaseDevOpsAgent):
    """Agent responsible for Azure cost optimization."""
    
    def __init__(self, subscription_id: str):
        super().__init__(
            name="CostOptimizer",
            description="Optimizes Azure costs and identifies savings opportunities",
            agent_type="cost_optimizer"
        )
        self.subscription_id = subscription_id
        self.capabilities = [
            "cost_analysis",
            "rightsizing_recommendations",
            "unused_resource_identification",
            "cost_by_tag_analysis",
            "cost_forecasting",
            "budget_recommendations"
        ]
        
    async def _setup_plugins(self):
        """Setup cost optimization plugins."""
        self.cost_plugin = CostOptimizerPlugin(self.subscription_id)
        
        if self.kernel:
            self.kernel.add_plugin(
                self.cost_plugin,
                "CostOptimizer"
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
            elif action == 'cost_by_tag':
                tag_name = params.get('tag_name', 'Environment')
                result = await self.cost_plugin.get_cost_by_tag(tag_name)
            else:
                # Use AI for analysis
                analysis_prompt = f"""
                Analyze this cost optimization request:
                Action: {action}
                Parameters: {params}
                
                Based on my capabilities: {self.capabilities}
                
                Provide cost optimization insights and recommendations.
                """
                result = await self.invoke_semantic_function(analysis_prompt)
                
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