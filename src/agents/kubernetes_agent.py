"""Kubernetes agent for AKS cluster management and monitoring."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from azure.mgmt.containerservice import ContainerServiceClient

from utils.azure_client import get_azure_client_manager
from agents.base_agent import BaseDevOpsAgent, DevOpsAgentPlugin
from semantic_kernel.functions import kernel_function


class KubernetesAgentPlugin(DevOpsAgentPlugin):
    """Plugin for Kubernetes/AKS management capabilities."""
    
    def __init__(self, cluster_config: Dict[str, Any], subscription_id: str):
        super().__init__("kubernetes_agent")
        self.cluster_config = cluster_config
        self.subscription_id = subscription_id
        self.azure_clients = get_azure_client_manager(subscription_id)
        self.k8s_clients = {}
        self._initialized = False
        
    async def initialize_k8s_clients(self):
        """Initialize Kubernetes clients for AKS clusters."""
        try:
            # Load kubeconfig if specified
            kubeconfig_path = self.cluster_config.get('kubeconfig_path')
            if kubeconfig_path and os.path.exists(os.path.expanduser(kubeconfig_path)):
                config.load_kube_config(config_file=os.path.expanduser(kubeconfig_path))
                self.k8s_clients['core'] = client.CoreV1Api()
                self.k8s_clients['apps'] = client.AppsV1Api()
                self.k8s_clients['batch'] = client.BatchV1Api()
                self.k8s_clients['networking'] = client.NetworkingV1Api()
                self._initialized = True
                self.logger.info("Kubernetes clients initialized from kubeconfig")
            else:
                # Try to use in-cluster config (if running in K8s)
                try:
                    config.load_incluster_config()
                    self.k8s_clients['core'] = client.CoreV1Api()
                    self.k8s_clients['apps'] = client.AppsV1Api()
                    self.k8s_clients['batch'] = client.BatchV1Api()
                    self.k8s_clients['networking'] = client.NetworkingV1Api()
                    self._initialized = True
                    self.logger.info("Kubernetes clients initialized from in-cluster config")
                except:
                    self.logger.warning("No Kubernetes configuration available")
        except Exception as e:
            self.logger.error(f"Error initializing Kubernetes clients: {str(e)}")
    
    @kernel_function(name="get_aks_clusters", description="List all AKS clusters in the subscription")
    async def get_aks_clusters(self) -> str:
        """Get all AKS clusters in the Azure subscription."""
        try:
            container_client = self.azure_clients.get_container_service_client()
            
            clusters = list(container_client.managed_clusters.list())
            
            result = f"AKS Clusters in Subscription:\n\n"
            result += f"📊 Total Clusters: {len(clusters)}\n\n"
            
            for cluster in clusters:
                result += f"🏗️ **{cluster.name}**\n"
                result += f"• Resource Group: {cluster.id.split('/')[4]}\n"
                result += f"• Location: {cluster.location}\n"
                result += f"• Kubernetes Version: {cluster.kubernetes_version}\n"
                result += f"• Node Pools: {len(cluster.agent_pool_profiles)}\n"
                
                # Calculate total nodes
                total_nodes = sum(pool.count for pool in cluster.agent_pool_profiles if pool.count)
                result += f"• Total Nodes: {total_nodes}\n"
                
                result += f"• Status: {cluster.provisioning_state}\n"
                result += f"• SKU: {cluster.sku.tier if cluster.sku else 'Free'}\n\n"
            
            if not clusters:
                result += "No AKS clusters found in the subscription.\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting AKS clusters: {str(e)}")
            return f"Error getting AKS clusters: {str(e)}"
    
    @kernel_function(name="get_cluster_status", description="Get comprehensive AKS cluster status")
    async def get_cluster_status(self, cluster_name: Optional[str] = None) -> str:
        """Get comprehensive Kubernetes cluster status."""
        try:
            # First, try to get AKS cluster info from Azure
            aks_info = ""
            if cluster_name:
                aks_info = await self._get_aks_cluster_info(cluster_name)
            
            # If K8s clients not initialized, try now
            if not self._initialized:
                await self.initialize_k8s_clients()
            
            if not self._initialized or not self.k8s_clients:
                # Return AKS info only
                return f"Kubernetes Cluster Status:\n\n{aks_info}\n\n⚠️ Direct cluster access not configured. Please set up kubeconfig to get detailed pod and service information."
            
            # Get cluster details from Kubernetes API
            result = f"Kubernetes Cluster Status:\n\n"
            
            if aks_info:
                result += f"{aks_info}\n"
            
            # Get nodes
            nodes = self.k8s_clients['core'].list_node()
            node_count = len(nodes.items)
            ready_nodes = sum(1 for node in nodes.items if self._is_node_ready(node))
            
            result += f"📊 Cluster Resources:\n"
            result += f"• Total Nodes: {node_count}\n"
            result += f"• Ready Nodes: {ready_nodes}\n"
            
            # Node details
            total_cpu = 0
            total_memory = 0
            for node in nodes.items:
                cpu = node.status.capacity.get('cpu', '0')
                memory = node.status.capacity.get('memory', '0Ki')
                total_cpu += int(cpu)
                total_memory += self._parse_memory(memory)
            
            result += f"• Total CPU: {total_cpu} cores\n"
            result += f"• Total Memory: {total_memory / (1024**3):.1f} GB\n\n"
            
            # Get namespace summary
            namespaces = self.k8s_clients['core'].list_namespace()
            result += f"📁 Namespaces: {len(namespaces.items)}\n"
            
            # Get pod summary
            all_pods = self.k8s_clients['core'].list_pod_for_all_namespaces()
            pod_status = {'Running': 0, 'Pending': 0, 'Failed': 0, 'Succeeded': 0, 'Unknown': 0}
            
            for pod in all_pods.items:
                status = pod.status.phase
                pod_status[status] = pod_status.get(status, 0) + 1
            
            result += f"\n🐳 Pod Status Summary:\n"
            result += f"• Total Pods: {len(all_pods.items)}\n"
            for status, count in pod_status.items():
                if count > 0:
                    result += f"• {status}: {count}\n"
            
            # Get services
            services = self.k8s_clients['core'].list_service_for_all_namespaces()
            result += f"\n🌐 Services: {len(services.items)}\n"
            
            # Get deployments
            deployments = self.k8s_clients['apps'].list_deployment_for_all_namespaces()
            ready_deployments = sum(1 for d in deployments.items 
                                  if d.status.ready_replicas == d.spec.replicas)
            result += f"\n🚀 Deployments:\n"
            result += f"• Total: {len(deployments.items)}\n"
            result += f"• Ready: {ready_deployments}\n"
            
            # Resource usage summary
            result += await self._get_resource_usage_summary()
            
            return result
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error: {str(e)}")
            return f"Error accessing Kubernetes cluster: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error getting cluster status: {str(e)}")
            return f"Error getting cluster status: {str(e)}"
    
    async def _get_aks_cluster_info(self, cluster_name: str) -> str:
        """Get AKS cluster information from Azure."""
        try:
            container_client = self.azure_clients.get_container_service_client()
            
            # Find the cluster
            clusters = list(container_client.managed_clusters.list())
            target_cluster = None
            
            for cluster in clusters:
                if cluster.name.lower() == cluster_name.lower():
                    target_cluster = cluster
                    break
            
            if not target_cluster:
                return f"AKS cluster '{cluster_name}' not found."
            
            result = f"🏗️ AKS Cluster: {target_cluster.name}\n"
            result += f"• Resource Group: {target_cluster.id.split('/')[4]}\n"
            result += f"• Location: {target_cluster.location}\n"
            result += f"• Version: {target_cluster.kubernetes_version}\n"
            result += f"• DNS Prefix: {target_cluster.dns_prefix}\n"
            result += f"• FQDN: {target_cluster.fqdn}\n"
            
            # Node pool information
            result += f"\n📊 Node Pools:\n"
            for pool in target_cluster.agent_pool_profiles:
                result += f"• {pool.name}: {pool.count} nodes ({pool.vm_size})\n"
                if pool.enable_auto_scaling:
                    result += f"  Auto-scaling: {pool.min_count}-{pool.max_count}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting AKS info: {str(e)}")
            return ""
    
    @kernel_function(name="get_pod_logs", description="Get logs from a specific pod")
    async def get_pod_logs(self, namespace: str, pod_name: str, lines: int = 100) -> str:
        """Get logs from a specific pod."""
        try:
            if not self._initialized:
                await self.initialize_k8s_clients()
                
            if not self._initialized:
                return "Kubernetes client not initialized. Please configure kubeconfig."
            
            self.logger.info(f"Getting logs for pod {pod_name} in namespace {namespace}")
            
            # Get pod to verify it exists
            try:
                pod = self.k8s_clients['core'].read_namespaced_pod(
                    name=pod_name,
                    namespace=namespace
                )
            except ApiException as e:
                if e.status == 404:
                    return f"Pod {namespace}/{pod_name} not found."
                raise
            
            # Get logs
            logs = self.k8s_clients['core'].read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=lines
            )
            
            result = f"Pod Logs - {namespace}/{pod_name} (Last {lines} lines):\n\n"
            result += f"Container: {pod.spec.containers[0].name}\n"
            result += f"Status: {pod.status.phase}\n"
            result += f"Node: {pod.spec.node_name}\n\n"
            result += "="*60 + "\n"
            result += logs
            
            return result
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error: {str(e)}")
            return f"Error getting pod logs: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error getting pod logs: {str(e)}")
            return f"Error getting pod logs: {str(e)}"
    
    @kernel_function(name="scale_deployment", description="Scale a Kubernetes deployment")
    async def scale_deployment(self, namespace: str, deployment_name: str, replicas: int) -> str:
        """Scale a Kubernetes deployment."""
        try:
            if not self._initialized:
                await self.initialize_k8s_clients()
                
            if not self._initialized:
                return "Kubernetes client not initialized. Please configure kubeconfig."
            
            self.logger.info(f"Scaling deployment {deployment_name} in namespace {namespace} to {replicas} replicas")
            
            # Get current deployment
            deployment = self.k8s_clients['apps'].read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            current_replicas = deployment.spec.replicas
            
            # Update replica count
            deployment.spec.replicas = replicas
            
            # Apply the change
            self.k8s_clients['apps'].patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body={'spec': {'replicas': replicas}}
            )
            
            result = f"Deployment Scaling:\n\n"
            result += f"✅ Successfully initiated scaling for {namespace}/{deployment_name}\n"
            result += f"• Previous Replicas: {current_replicas}\n"
            result += f"• Target Replicas: {replicas}\n"
            result += f"• Change: {replicas - current_replicas:+d}\n\n"
            
            # Wait a moment and check status
            await asyncio.sleep(2)
            
            # Get updated deployment
            updated = self.k8s_clients['apps'].read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            result += f"📊 Current Status:\n"
            result += f"• Desired Replicas: {updated.spec.replicas}\n"
            result += f"• Current Replicas: {updated.status.replicas or 0}\n"
            result += f"• Ready Replicas: {updated.status.ready_replicas or 0}\n"
            result += f"• Available Replicas: {updated.status.available_replicas or 0}\n"
            
            if updated.status.conditions:
                latest_condition = updated.status.conditions[-1]
                result += f"\n📋 Latest Condition:\n"
                result += f"• Type: {latest_condition.type}\n"
                result += f"• Status: {latest_condition.status}\n"
                result += f"• Reason: {latest_condition.reason}\n"
            
            return result
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error: {str(e)}")
            return f"Error scaling deployment: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error scaling deployment: {str(e)}")
            return f"Error scaling deployment: {str(e)}"
    
    @kernel_function(name="get_resource_usage", description="Get resource usage for cluster or namespace")
    async def get_resource_usage(self, namespace: Optional[str] = None) -> str:
        """Get resource usage for cluster or specific namespace."""
        try:
            if not self._initialized:
                await self.initialize_k8s_clients()
                
            if not self._initialized:
                return "Kubernetes client not initialized. Please configure kubeconfig."
            
            scope = f"namespace '{namespace}'" if namespace else "entire cluster"
            self.logger.info(f"Getting resource usage for {scope}")
            
            result = f"Resource Usage Report - {scope}:\n\n"
            
            # Get pods
            if namespace:
                pods = self.k8s_clients['core'].list_namespaced_pod(namespace)
            else:
                pods = self.k8s_clients['core'].list_pod_for_all_namespaces()
            
            # Calculate resource requests and limits
            total_cpu_requests = 0
            total_cpu_limits = 0
            total_memory_requests = 0
            total_memory_limits = 0
            pod_count = len(pods.items)
            
            for pod in pods.items:
                for container in pod.spec.containers:
                    if container.resources:
                        if container.resources.requests:
                            cpu_req = container.resources.requests.get('cpu', '0')
                            mem_req = container.resources.requests.get('memory', '0')
                            total_cpu_requests += self._parse_cpu(cpu_req)
                            total_memory_requests += self._parse_memory(mem_req)
                        
                        if container.resources.limits:
                            cpu_lim = container.resources.limits.get('cpu', '0')
                            mem_lim = container.resources.limits.get('memory', '0')
                            total_cpu_limits += self._parse_cpu(cpu_lim)
                            total_memory_limits += self._parse_memory(mem_lim)
            
            result += f"📊 Resource Summary:\n"
            result += f"• Total Pods: {pod_count}\n\n"
            
            result += f"💻 CPU:\n"
            result += f"• Total Requests: {total_cpu_requests:.2f} cores\n"
            result += f"• Total Limits: {total_cpu_limits:.2f} cores\n"
            result += f"• Average per Pod: {total_cpu_requests/pod_count:.2f} cores\n\n" if pod_count > 0 else "\n"
            
            result += f"🧠 Memory:\n"
            result += f"• Total Requests: {total_memory_requests/(1024**3):.2f} GB\n"
            result += f"• Total Limits: {total_memory_limits/(1024**3):.2f} GB\n"
            result += f"• Average per Pod: {total_memory_requests/(1024**3)/pod_count:.2f} GB\n\n" if pod_count > 0 else "\n"
            
            # Top resource consumers
            if pods.items:
                result += "🔝 Top Resource Consumers:\n"
                
                # Sort pods by CPU requests
                pod_resources = []
                for pod in pods.items:
                    cpu_req = 0
                    mem_req = 0
                    for container in pod.spec.containers:
                        if container.resources and container.resources.requests:
                            cpu_req += self._parse_cpu(container.resources.requests.get('cpu', '0'))
                            mem_req += self._parse_memory(container.resources.requests.get('memory', '0'))
                    
                    pod_resources.append({
                        'name': pod.metadata.name,
                        'namespace': pod.metadata.namespace,
                        'cpu': cpu_req,
                        'memory': mem_req
                    })
                
                # Top 5 by CPU
                top_cpu = sorted(pod_resources, key=lambda x: x['cpu'], reverse=True)[:5]
                result += "\nBy CPU:\n"
                for i, pod in enumerate(top_cpu, 1):
                    result += f"{i}. {pod['namespace']}/{pod['name']}: {pod['cpu']:.2f} cores\n"
                
                # Top 5 by Memory
                top_mem = sorted(pod_resources, key=lambda x: x['memory'], reverse=True)[:5]
                result += "\nBy Memory:\n"
                for i, pod in enumerate(top_mem, 1):
                    result += f"{i}. {pod['namespace']}/{pod['name']}: {pod['memory']/(1024**3):.2f} GB\n"
            
            return result
            
        except ApiException as e:
            self.logger.error(f"Kubernetes API error: {str(e)}")
            return f"Error getting resource usage: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error getting resource usage: {str(e)}")
            return f"Error getting resource usage: {str(e)}"
    
    async def _get_resource_usage_summary(self) -> str:
        """Get cluster-wide resource usage summary."""
        try:
            if not self._initialized:
                return ""
            
            # Get node metrics if available
            try:
                # This requires metrics-server to be installed
                from kubernetes.client import CustomObjectsApi
                custom_api = CustomObjectsApi()
                
                node_metrics = custom_api.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="nodes"
                )
                
                result = "\n📈 Current Resource Usage:\n"
                
                for node in node_metrics.get('items', []):
                    node_name = node['metadata']['name']
                    cpu_usage = self._parse_cpu(node['usage']['cpu'])
                    memory_usage = self._parse_memory(node['usage']['memory'])
                    
                    result += f"• {node_name}: CPU {cpu_usage:.1f} cores, Memory {memory_usage/(1024**3):.1f} GB\n"
                
                return result
                
            except:
                # Metrics server not available
                return "\n💡 Install metrics-server for real-time resource usage data.\n"
                
        except Exception as e:
            self.logger.warning(f"Could not get resource metrics: {str(e)}")
            return ""
    
    def _is_node_ready(self, node) -> bool:
        """Check if a node is ready."""
        if node.status.conditions:
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    return condition.status == "True"
        return False
    
    def _parse_cpu(self, cpu_str: str) -> float:
        """Parse CPU string to float (in cores)."""
        if not cpu_str or cpu_str == '0':
            return 0.0
        
        cpu_str = str(cpu_str)
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1]) / 1000
        elif cpu_str.endswith('n'):
            return float(cpu_str[:-1]) / 1000000000
        else:
            return float(cpu_str)
    
    def _parse_memory(self, mem_str: str) -> float:
        """Parse memory string to float (in bytes)."""
        if not mem_str or mem_str == '0':
            return 0.0
        
        mem_str = str(mem_str)
        
        # Remove 'i' suffix if present (e.g., Ki, Mi, Gi)
        if mem_str.endswith('i'):
            mem_str = mem_str[:-1]
            
        if mem_str.endswith('K'):
            return float(mem_str[:-1]) * 1024
        elif mem_str.endswith('M'):
            return float(mem_str[:-1]) * 1024 * 1024
        elif mem_str.endswith('G'):
            return float(mem_str[:-1]) * 1024 * 1024 * 1024
        elif mem_str.endswith('T'):
            return float(mem_str[:-1]) * 1024 * 1024 * 1024 * 1024
        else:
            return float(mem_str)
    
    @kernel_function(name="analyze_cluster_health", description="Analyze AKS cluster health using AI")
    async def analyze_cluster_health(self, cluster_name: Optional[str] = None) -> str:
        """Use AI to analyze cluster health and provide recommendations."""
        try:
            # Get cluster status
            status = await self.get_cluster_status(cluster_name)
            
            if hasattr(self, 'agent'):
                health_prompt = f"""
                Analyze the following Kubernetes/AKS cluster status:
                
                {status}
                
                Provide:
                1. Overall health assessment
                2. Potential issues or risks
                3. Performance optimization recommendations
                4. Security considerations
                5. Scaling recommendations
                6. Best practices that should be implemented
                
                Focus on actionable insights.
                """
                
                analysis = await self.agent.invoke_semantic_function(health_prompt)
                
                result = f"🤖 AI-Powered Cluster Analysis:\n\n{analysis}"
                return result
            else:
                return "AI analysis requires model configuration."
                
        except Exception as e:
            self.logger.error(f"Error analyzing cluster health: {str(e)}")
            return f"Error analyzing cluster health: {str(e)}"


class KubernetesAgent(BaseDevOpsAgent):
    """Agent responsible for Kubernetes/AKS cluster management."""
    
    def __init__(self, cluster_config: Dict[str, Any]):
        super().__init__(
            name="KubernetesAgent",
            description="Manages Kubernetes/AKS clusters and workloads",
            agent_type="kubernetes_agent"
        )
        self.cluster_config = cluster_config
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID', '')
        self.capabilities = [
            "aks_cluster_management",
            "cluster_monitoring",
            "pod_management",
            "resource_scaling",
            "log_analysis",
            "resource_usage_analysis",
            "ai_health_analysis"
        ]
        
    async def _setup_plugins(self):
        """Setup Kubernetes management plugins."""
        self.k8s_plugin = KubernetesAgentPlugin(self.cluster_config, self.subscription_id)
        self.k8s_plugin.agent = self  # Give plugin access to agent
        
        # Initialize Kubernetes clients
        await self.k8s_plugin.initialize_k8s_clients()
        
        if self.kernel:
            self.kernel.add_plugin(
                self.k8s_plugin,
                "KubernetesAgent"
            )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process Kubernetes management requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'list_clusters':
                result = await self.k8s_plugin.get_aks_clusters()
                
            elif action == 'get_cluster_status':
                cluster_name = params.get('cluster_name')
                result = await self.k8s_plugin.get_cluster_status(cluster_name)
                
            elif action == 'get_pod_logs':
                namespace = params.get('namespace', 'default')
                pod_name = params.get('pod_name', '')
                lines = params.get('lines', 100)
                result = await self.k8s_plugin.get_pod_logs(namespace, pod_name, lines)
                
            elif action == 'scale_deployment':
                namespace = params.get('namespace', 'default')
                deployment_name = params.get('deployment_name', '')
                replicas = params.get('replicas', 1)
                result = await self.k8s_plugin.scale_deployment(namespace, deployment_name, replicas)
                
            elif action == 'get_resource_usage':
                namespace = params.get('namespace')
                result = await self.k8s_plugin.get_resource_usage(namespace)
                
            elif action == 'analyze_health':
                cluster_name = params.get('cluster_name')
                result = await self.k8s_plugin.analyze_cluster_health(cluster_name)
                
            else:
                # Use AI for unknown requests
                analysis_prompt = f"""
                Analyze this Kubernetes request:
                Action: {action}
                Parameters: {params}
                
                Based on my Kubernetes capabilities: {self.capabilities}
                
                Provide guidance on handling this request.
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