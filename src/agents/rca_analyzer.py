"""Root Cause Analysis agent for DevOps incidents using Azure Monitor and AI."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure.monitor.query import LogsQueryStatus
from azure.core.exceptions import AzureError

from utils.azure_client import get_azure_client_manager
from agents.base_agent import BaseDevOpsAgent, DevOpsAgentPlugin
from semantic_kernel.functions import kernel_function


class RCAAnalyzerPlugin(DevOpsAgentPlugin):
    """Plugin for root cause analysis capabilities."""
    
    def __init__(self, subscription_id: str):
        super().__init__("rca_analyzer")
        self.subscription_id = subscription_id
        self.azure_clients = get_azure_client_manager(subscription_id)
        
    @kernel_function(name="analyze_incident", description="Perform root cause analysis on an incident")
    async def analyze_incident(self, incident_data: Dict[str, Any]) -> str:
        """Analyze an incident using Azure Monitor logs and AI-powered analysis."""
        try:
            self.logger.info(f"Analyzing incident: {incident_data.get('title', 'Unknown')}")
            
            # Extract incident details
            incident_type = incident_data.get('type', 'unknown')
            symptoms = incident_data.get('symptoms', [])
            affected_resources = incident_data.get('affected_resources', [])
            time_window = incident_data.get('time_window', {'hours': 2})
            workspace_id = incident_data.get('workspace_id')
            
            result = f"Root Cause Analysis Report:\n\n"
            result += f"📋 Incident: {incident_data.get('title', 'Untitled Incident')}\n"
            result += f"• Type: {incident_type}\n"
            result += f"• Time: {datetime.utcnow().isoformat()}\n\n"
            
            # Collect diagnostic data
            diagnostic_data = await self._collect_diagnostic_data(
                affected_resources, 
                symptoms,
                time_window,
                workspace_id
            )
            
            # Analyze logs for patterns
            log_analysis = await self._analyze_logs(
                diagnostic_data.get('logs', []),
                symptoms
            )
            
            # Get metrics anomalies
            metric_anomalies = await self._detect_metric_anomalies(
                affected_resources,
                time_window
            )
            
            # Perform AI-powered root cause analysis
            ai_analysis = await self._ai_root_cause_analysis(
                incident_data,
                diagnostic_data,
                log_analysis,
                metric_anomalies
            )
            
            # Format comprehensive report
            result += ai_analysis
            
            # Add remediation steps
            remediation = await self._generate_remediation_plan(
                incident_type,
                ai_analysis
            )
            
            result += f"\n🔧 Remediation Steps:\n{remediation}\n"
            
            # Historical correlation
            similar_incidents = await self._find_similar_incidents(
                incident_data,
                workspace_id
            )
            
            if similar_incidents:
                result += f"\n📊 Historical Correlation:\n"
                result += f"Found {len(similar_incidents)} similar incidents in the past 30 days.\n"
                for incident in similar_incidents[:3]:
                    result += f"• {incident['date']}: {incident['description']}\n"
                    result += f"  Resolution: {incident['resolution']}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing incident: {str(e)}")
            return f"Error during RCA analysis: {str(e)}"
    
    async def _collect_diagnostic_data(
        self, 
        affected_resources: List[str], 
        symptoms: List[str],
        time_window: Dict[str, int],
        workspace_id: Optional[str]
    ) -> Dict[str, Any]:
        """Collect diagnostic data from Azure Monitor."""
        diagnostic_data = {
            'logs': [],
            'metrics': [],
            'alerts': []
        }
        
        try:
            if not workspace_id:
                # Try to get default workspace
                log_analytics_client = self.azure_clients.get_log_analytics_client()
                workspaces = list(log_analytics_client.workspaces.list())
                if workspaces:
                    workspace_id = workspaces[0].customer_id
                else:
                    self.logger.warning("No Log Analytics workspace found")
                    return diagnostic_data
            
            logs_client = self.azure_clients.get_logs_query_client()
            
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_window.get('hours', 2))
            timespan = (start_time, end_time)
            
            # Build dynamic query based on symptoms
            query_parts = []
            
            # Error logs query
            if any('error' in symptom.lower() for symptom in symptoms):
                query_parts.append("""
                AzureDiagnostics
                | where TimeGenerated between (ago(2h) .. now())
                | where Level == "Error" or Level == "Critical"
                | project TimeGenerated, Resource, Level, Message
                | order by TimeGenerated desc
                | limit 100
                """)
            
            # Performance issues query
            if any('slow' in symptom.lower() or 'performance' in symptom.lower() for symptom in symptoms):
                query_parts.append("""
                AzureMetrics
                | where TimeGenerated between (ago(2h) .. now())
                | where MetricName in ("Percentage CPU", "Available Memory Bytes", "Response Time")
                | summarize AvgValue = avg(Average), MaxValue = max(Maximum) by Resource, MetricName
                | where AvgValue > 80 or MaxValue > 90
                """)
            
            # Execute queries
            for query in query_parts:
                try:
                    response = logs_client.query_workspace(
                        workspace_id=workspace_id,
                        query=query,
                        timespan=timespan
                    )
                    
                    if response.status == LogsQueryStatus.SUCCESS:
                        for table in response.tables:
                            for row in table.rows:
                                diagnostic_data['logs'].append({
                                    'columns': table.columns,
                                    'data': row
                                })
                except Exception as e:
                    self.logger.warning(f"Query execution failed: {str(e)}")
            
            # Get recent alerts
            monitor_client = self.azure_clients.get_monitor_client()
            filter_str = f"eventTimestamp ge '{start_time.isoformat()}'"
            
            try:
                alerts = monitor_client.activity_logs.list(filter=filter_str)
                for alert in alerts:
                    if hasattr(alert, 'category') and alert.category.value == 'Alert':
                        diagnostic_data['alerts'].append({
                            'time': alert.event_timestamp,
                            'resource': alert.resource_id,
                            'description': alert.description
                        })
            except:
                pass
            
        except Exception as e:
            self.logger.error(f"Error collecting diagnostic data: {str(e)}")
        
        return diagnostic_data
    
    async def _analyze_logs(self, logs: List[Dict], symptoms: List[str]) -> Dict[str, Any]:
        """Analyze log patterns for root cause indicators."""
        analysis = {
            'error_patterns': {},
            'timeline': [],
            'affected_components': set(),
            'severity': 'Medium'
        }
        
        try:
            # Analyze error patterns
            for log_entry in logs:
                if 'data' in log_entry:
                    # Extract relevant fields based on columns
                    columns = log_entry.get('columns', [])
                    data = log_entry.get('data', [])
                    
                    # Create a dict from columns and data
                    log_dict = {}
                    for i, col in enumerate(columns):
                        if i < len(data):
                            log_dict[col] = data[i]
                    
                    # Track error patterns
                    if 'Message' in log_dict:
                        message = str(log_dict['Message'])
                        # Extract error type
                        if 'Exception' in message:
                            error_type = message.split('Exception')[0].split()[-1] + 'Exception'
                            analysis['error_patterns'][error_type] = analysis['error_patterns'].get(error_type, 0) + 1
                        elif 'Error' in message:
                            error_type = 'Generic Error'
                            analysis['error_patterns'][error_type] = analysis['error_patterns'].get(error_type, 0) + 1
                    
                    # Track affected components
                    if 'Resource' in log_dict:
                        analysis['affected_components'].add(str(log_dict['Resource']))
                    
                    # Build timeline
                    if 'TimeGenerated' in log_dict:
                        analysis['timeline'].append({
                            'time': str(log_dict['TimeGenerated']),
                            'event': log_dict.get('Message', 'Unknown event')[:100]
                        })
            
            # Determine severity
            total_errors = sum(analysis['error_patterns'].values())
            if total_errors > 100:
                analysis['severity'] = 'Critical'
            elif total_errors > 50:
                analysis['severity'] = 'High'
            elif total_errors > 10:
                analysis['severity'] = 'Medium'
            else:
                analysis['severity'] = 'Low'
            
            # Convert set to list for JSON serialization
            analysis['affected_components'] = list(analysis['affected_components'])
            
        except Exception as e:
            self.logger.error(f"Error analyzing logs: {str(e)}")
        
        return analysis
    
    async def _detect_metric_anomalies(
        self, 
        affected_resources: List[str], 
        time_window: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in resource metrics."""
        anomalies = []
        
        try:
            metrics_client = self.azure_clients.get_metrics_query_client()
            monitor_client = self.azure_clients.get_monitor_client()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_window.get('hours', 2))
            
            for resource_id in affected_resources[:5]:  # Limit to 5 resources
                try:
                    # Determine metrics based on resource type
                    if '/virtualmachines/' in resource_id.lower():
                        metric_names = ["Percentage CPU", "Available Memory Bytes"]
                    elif '/storageaccounts/' in resource_id.lower():
                        metric_names = ["UsedCapacity", "Availability"]
                    else:
                        continue
                    
                    # Query metrics
                    response = await metrics_client.query_resource(
                        resource_uri=resource_id,
                        metric_names=metric_names,
                        timespan=(start_time, end_time),
                        granularity=timedelta(minutes=5)
                    )
                    
                    for metric in response.metrics:
                        if metric.timeseries:
                            for timeseries in metric.timeseries:
                                values = [d.average for d in timeseries.data if d.average is not None]
                                
                                if values:
                                    avg_value = sum(values) / len(values)
                                    max_value = max(values)
                                    
                                    # Detect anomalies (simple threshold-based)
                                    if metric.name == "Percentage CPU" and max_value > 90:
                                        anomalies.append({
                                            'resource': resource_id.split('/')[-1],
                                            'metric': metric.name,
                                            'anomaly': 'High CPU usage',
                                            'max_value': max_value,
                                            'avg_value': avg_value
                                        })
                                    elif metric.name == "Available Memory Bytes" and avg_value < 1073741824:  # Less than 1GB
                                        anomalies.append({
                                            'resource': resource_id.split('/')[-1],
                                            'metric': metric.name,
                                            'anomaly': 'Low available memory',
                                            'avg_value': avg_value / (1024**3)  # Convert to GB
                                        })
                
                except Exception as e:
                    self.logger.warning(f"Could not analyze metrics for {resource_id}: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error detecting metric anomalies: {str(e)}")
        
        return anomalies
    
    async def _ai_root_cause_analysis(
        self,
        incident_data: Dict[str, Any],
        diagnostic_data: Dict[str, Any],
        log_analysis: Dict[str, Any],
        metric_anomalies: List[Dict[str, Any]]
    ) -> str:
        """Use AI to perform deep root cause analysis."""
        
        # Prepare data for AI analysis
        analysis_context = f"""
        Incident Details:
        - Title: {incident_data.get('title', 'Unknown')}
        - Type: {incident_data.get('type', 'Unknown')}
        - Symptoms: {', '.join(incident_data.get('symptoms', []))}
        - Affected Resources: {', '.join(incident_data.get('affected_resources', [])[:5])}
        
        Log Analysis:
        - Error Patterns: {json.dumps(log_analysis.get('error_patterns', {}), indent=2)}
        - Severity: {log_analysis.get('severity', 'Unknown')}
        - Affected Components: {', '.join(log_analysis.get('affected_components', [])[:10])}
        
        Metric Anomalies:
        {json.dumps(metric_anomalies[:5], indent=2) if metric_anomalies else 'No significant anomalies detected'}
        
        Recent Alerts: {len(diagnostic_data.get('alerts', []))} alerts triggered
        
        Based on this data, perform a comprehensive root cause analysis. Identify:
        1. The most likely root cause(s)
        2. Contributing factors
        3. Impact assessment
        4. Evidence supporting your conclusions
        """
        
        # Use the agent's AI model for analysis
        ai_prompt = f"""
        As an expert DevOps engineer specializing in root cause analysis, analyze the following incident:
        
        {analysis_context}
        
        Provide a detailed root cause analysis with:
        - Primary root cause (be specific)
        - Secondary contributing factors
        - Timeline of events
        - Impact on system components
        - Confidence level in the analysis
        """
        
        ai_result = await self.agent.invoke_semantic_function(ai_prompt)
        
        # Format the AI analysis
        formatted_result = f"🔍 AI-Powered Root Cause Analysis:\n\n{ai_result}\n"
        
        # Add specific findings from data
        if log_analysis.get('error_patterns'):
            formatted_result += f"\n📊 Error Pattern Summary:\n"
            for error_type, count in sorted(log_analysis['error_patterns'].items(), key=lambda x: x[1], reverse=True)[:5]:
                formatted_result += f"• {error_type}: {count} occurrences\n"
        
        if metric_anomalies:
            formatted_result += f"\n⚠️ Metric Anomalies Detected:\n"
            for anomaly in metric_anomalies[:5]:
                formatted_result += f"• {anomaly['resource']}: {anomaly['anomaly']}\n"
        
        return formatted_result
    
    async def _generate_remediation_plan(self, incident_type: str, ai_analysis: str) -> str:
        """Generate a remediation plan based on the analysis."""
        
        remediation_prompt = f"""
        Based on the following root cause analysis for a {incident_type} incident:
        
        {ai_analysis[:1000]}  # Limit context size
        
        Generate a prioritized remediation plan with:
        1. Immediate actions (to resolve the current incident)
        2. Short-term fixes (to prevent recurrence in the next 24-48 hours)
        3. Long-term improvements (to prevent similar incidents)
        
        For each action, specify:
        - What to do
        - Expected impact
        - Estimated time to implement
        - Resources required
        """
        
        remediation_plan = await self.agent.invoke_semantic_function(remediation_prompt)
        
        return remediation_plan
    
    async def _find_similar_incidents(
        self,
        incident_data: Dict[str, Any],
        workspace_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Find similar historical incidents."""
        similar_incidents = []
        
        try:
            if not workspace_id:
                return similar_incidents
            
            logs_client = self.azure_clients.get_logs_query_client()
            
            # Query for similar patterns in the last 30 days
            symptoms_filter = " or ".join([f'Message contains "{symptom}"' for symptom in incident_data.get('symptoms', [])])
            
            query = f"""
            AzureDiagnostics
            | where TimeGenerated > ago(30d)
            | where Level in ("Error", "Critical")
            | where {symptoms_filter}
            | summarize Count = count() by bin(TimeGenerated, 1d), Resource
            | where Count > 10
            | order by TimeGenerated desc
            | limit 10
            """
            
            response = logs_client.query_workspace(
                workspace_id=workspace_id,
                query=query,
                timespan=timedelta(days=30)
            )
            
            if response.status == LogsQueryStatus.SUCCESS and response.tables:
                for table in response.tables:
                    for row in table.rows:
                        similar_incidents.append({
                            'date': str(row[0]) if row[0] else 'Unknown',
                            'resource': str(row[1]) if len(row) > 1 else 'Unknown',
                            'count': row[2] if len(row) > 2 else 0,
                            'description': f"Similar error pattern on {row[1] if len(row) > 1 else 'Unknown'}",
                            'resolution': 'Review historical logs for resolution details'
                        })
        
        except Exception as e:
            self.logger.warning(f"Could not search for similar incidents: {str(e)}")
        
        return similar_incidents[:5]  # Return top 5
    
    @kernel_function(name="analyze_alert", description="Analyze a specific Azure Monitor alert")
    async def analyze_alert(self, alert_id: str) -> str:
        """Analyze a specific alert from Azure Monitor."""
        try:
            monitor_client = self.azure_clients.get_monitor_client()
            
            # Get alert details
            # Note: This is a simplified version. In production, you'd use the alert ID to get full details
            
            result = f"Alert Analysis:\n\n"
            result += f"📢 Alert ID: {alert_id}\n"
            
            # Query recent alerts
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            filter_str = f"eventTimestamp ge '{start_time.isoformat()}' and category eq 'Alert'"
            
            events = list(monitor_client.activity_logs.list(filter=filter_str))
            
            alert_found = False
            for event in events:
                if alert_id in str(event.event_name.value):
                    alert_found = True
                    result += f"• Time: {event.event_timestamp}\n"
                    result += f"• Resource: {event.resource_id}\n"
                    result += f"• Status: {event.status.value}\n"
                    result += f"• Description: {event.description}\n"
                    
                    # Analyze the alert
                    incident_data = {
                        'title': f"Alert: {event.event_name.value}",
                        'type': 'alert',
                        'symptoms': [event.description or 'Alert triggered'],
                        'affected_resources': [event.resource_id] if event.resource_id else []
                    }
                    
                    # Perform root cause analysis
                    rca_result = await self.analyze_incident(incident_data)
                    result += f"\n{rca_result}"
                    break
            
            if not alert_found:
                result += "Alert not found in recent activity log. The alert may be older than 24 hours.\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing alert: {str(e)}")
            return f"Error analyzing alert: {str(e)}"


class RCAAnalyzerAgent(BaseDevOpsAgent):
    """Agent responsible for root cause analysis of incidents."""
    
    def __init__(self, subscription_id: str = None):
        super().__init__(
            name="RCAAnalyzer",
            description="Performs AI-powered root cause analysis for DevOps incidents",
            agent_type="rca_analyzer"
        )
        self.subscription_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
        self.capabilities = [
            "incident_analysis",
            "log_pattern_analysis",
            "metric_anomaly_detection",
            "ai_root_cause_analysis",
            "remediation_planning",
            "historical_correlation",
            "alert_analysis"
        ]
        
    async def _setup_plugins(self):
        """Setup RCA analysis plugins."""
        self.rca_plugin = RCAAnalyzerPlugin(self.subscription_id)
        self.rca_plugin.agent = self  # Give plugin access to agent for AI functions
        
        if self.kernel:
            self.kernel.add_plugin(
                self.rca_plugin,
                "RCAAnalyzer"
            )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process RCA analysis requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'analyze_incident':
                incident_data = params.get('incident_data', {})
                
                # Ensure we have minimum required data
                if not incident_data.get('title'):
                    incident_data['title'] = 'Untitled Incident'
                if not incident_data.get('symptoms'):
                    incident_data['symptoms'] = ['System issue detected']
                
                result = await self.rca_plugin.analyze_incident(incident_data)
                
            elif action == 'analyze_alert':
                alert_id = params.get('alert_id', '')
                result = await self.rca_plugin.analyze_alert(alert_id)
                
            else:
                # Use AI for unknown requests
                analysis_prompt = f"""
                Analyze this root cause analysis request:
                Action: {action}
                Parameters: {params}
                
                Based on my RCA capabilities: {self.capabilities}
                
                Provide guidance on how to investigate and analyze this issue.
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