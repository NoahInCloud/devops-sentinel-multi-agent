"""Root Cause Analysis agent for DevOps incidents."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import BaseDevOpsAgent, DevOpsAgentPlugin


class RCAAnalyzerPlugin(DevOpsAgentPlugin):
    """Plugin for root cause analysis capabilities."""
    
    def __init__(self):
        super().__init__("rca_analyzer")
        self.incident_patterns = {}
        self.known_issues = []
        
    async def analyze_incident(self, incident_data: Dict[str, Any]) -> str:
        """Analyze an incident and provide root cause analysis."""
        try:
            self.logger.info(f"Analyzing incident: {incident_data.get('title', 'Unknown')}")
            
            incident_type = incident_data.get('type', 'unknown')
            symptoms = incident_data.get('symptoms', [])
            affected_resources = incident_data.get('affected_resources', [])
            timeline = incident_data.get('timeline', [])
            
            analysis_result = {
                'incident_id': incident_data.get('id', 'unknown'),
                'severity': self._assess_severity(incident_data),
                'probable_causes': self._identify_probable_causes(symptoms, affected_resources),
                'recommended_actions': self._get_recommended_actions(incident_type, symptoms),
                'similar_incidents': self._find_similar_incidents(incident_data),
                'analysis_confidence': self._calculate_confidence(incident_data)
            }
            
            # Format the analysis as a readable string
            result = f"Root Cause Analysis Report:\n\n"
            result += f"Incident ID: {analysis_result['incident_id']}\n"
            result += f"Severity: {analysis_result['severity']}\n"
            result += f"Analysis Confidence: {analysis_result['analysis_confidence']}%\n\n"
            
            result += "Probable Root Causes:\n"
            for i, cause in enumerate(analysis_result['probable_causes'], 1):
                result += f"{i}. {cause['cause']} (Probability: {cause['probability']}%)\n"
                result += f"   Evidence: {cause['evidence']}\n\n"
            
            result += "Recommended Actions:\n"
            for i, action in enumerate(analysis_result['recommended_actions'], 1):
                result += f"{i}. {action['action']} (Priority: {action['priority']})\n"
                result += f"   Expected Impact: {action['impact']}\n\n"
            
            if analysis_result['similar_incidents']:
                result += "Similar Historical Incidents:\n"
                for incident in analysis_result['similar_incidents']:
                    result += f"- {incident['date']}: {incident['description']}\n"
                    result += f"  Resolution: {incident['resolution']}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing incident: {str(e)}")
            return f"Error during RCA analysis: {str(e)}"
    
    def _assess_severity(self, incident_data: Dict[str, Any]) -> str:
        """Assess the severity of an incident."""
        affected_users = incident_data.get('affected_users', 0)
        downtime_minutes = incident_data.get('downtime_minutes', 0)
        business_impact = incident_data.get('business_impact', 'low')
        
        if affected_users > 1000 or downtime_minutes > 60 or business_impact == 'critical':
            return 'Critical'
        elif affected_users > 100 or downtime_minutes > 15 or business_impact == 'high':
            return 'High'
        elif affected_users > 10 or downtime_minutes > 5 or business_impact == 'medium':
            return 'Medium'
        else:
            return 'Low'
    
    def _identify_probable_causes(self, symptoms: List[str], affected_resources: List[str]) -> List[Dict[str, Any]]:
        """Identify probable root causes based on symptoms and affected resources."""
        causes = []
        
        # Network-related issues
        if any('timeout' in symptom.lower() or 'connection' in symptom.lower() for symptom in symptoms):
            causes.append({
                'cause': 'Network connectivity issues',
                'probability': 75,
                'evidence': 'Connection timeouts and network errors reported'
            })
        
        # Resource exhaustion
        if any('cpu' in resource.lower() or 'memory' in resource.lower() for resource in affected_resources):
            causes.append({
                'cause': 'Resource exhaustion (CPU/Memory)',
                'probability': 80,
                'evidence': 'High resource utilization detected'
            })
        
        # Database issues
        if any('database' in resource.lower() or 'sql' in resource.lower() for resource in affected_resources):
            causes.append({
                'cause': 'Database performance degradation',
                'probability': 70,
                'evidence': 'Database resources affected'
            })
        
        # Default cause if no specific pattern matches
        if not causes:
            causes.append({
                'cause': 'Configuration or deployment issue',
                'probability': 60,
                'evidence': 'No specific pattern identified, likely configuration related'
            })
        
        return causes
    
    def _get_recommended_actions(self, incident_type: str, symptoms: List[str]) -> List[Dict[str, Any]]:
        """Get recommended actions for incident resolution."""
        actions = []
        
        # Standard actions based on incident type
        if incident_type == 'performance':
            actions.extend([
                {
                    'action': 'Scale up affected resources',
                    'priority': 'High',
                    'impact': 'Immediate performance improvement'
                },
                {
                    'action': 'Analyze resource metrics and optimize',
                    'priority': 'Medium',
                    'impact': 'Long-term performance stability'
                }
            ])
        elif incident_type == 'availability':
            actions.extend([
                {
                    'action': 'Restart affected services',
                    'priority': 'Critical',
                    'impact': 'Restore service availability'
                },
                {
                    'action': 'Implement health checks and monitoring',
                    'priority': 'Medium',
                    'impact': 'Prevent future availability issues'
                }
            ])
        else:
            actions.append({
                'action': 'Investigate logs and monitor system behavior',
                'priority': 'High',
                'impact': 'Identify specific root cause'
            })
        
        return actions
    
    def _find_similar_incidents(self, incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar historical incidents."""
        # Mock historical incidents for demonstration
        return [
            {
                'date': '2024-03-15',
                'description': 'Database connection timeout during peak hours',
                'resolution': 'Increased connection pool size and optimized queries'
            },
            {
                'date': '2024-02-28',
                'description': 'High CPU usage causing application slowdown',
                'resolution': 'Scaled out application instances and implemented caching'
            }
        ]
    
    def _calculate_confidence(self, incident_data: Dict[str, Any]) -> int:
        """Calculate confidence level of the analysis."""
        confidence = 50  # Base confidence
        
        # Increase confidence based on available data
        if incident_data.get('symptoms'):
            confidence += 20
        if incident_data.get('affected_resources'):
            confidence += 15
        if incident_data.get('timeline'):
            confidence += 10
        if incident_data.get('logs'):
            confidence += 5
        
        return min(confidence, 95)  # Cap at 95%


class RCAAnalyzerAgent(BaseDevOpsAgent):
    """Agent responsible for root cause analysis of incidents."""
    
    def __init__(self):
        super().__init__("RCAAnalyzer", "Performs root cause analysis for DevOps incidents")
        self.capabilities = [
            "incident_analysis",
            "pattern_recognition", 
            "historical_correlation",
            "resolution_recommendations"
        ]
        
    async def _setup_plugins(self):
        """Setup RCA analysis plugins."""
        self.rca_plugin = RCAAnalyzerPlugin()
        self.kernel.add_plugin(
            plugin=self.rca_plugin,
            plugin_name="rca_analyzer", 
            description="Root cause analysis capabilities"
        )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process RCA analysis requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'analyze_incident':
                incident_data = params.get('incident_data', {})
                result = await self.rca_plugin.analyze_incident(incident_data)
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