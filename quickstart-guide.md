# DevOps Sentinel Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Python 3.8+
- Azure Subscription
- Azure CLI (optional but recommended)
- Node.js (optional, for Azure MCP)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd devops-sentinel-multi-agent

# Run the setup script
python setup.py
```

### 2. Configure Azure OpenAI
1. Create an Azure OpenAI resource in the Azure Portal
2. Deploy models (recommended: gpt-35-turbo and gpt-4)
3. Update `.env` with your endpoint and key:
```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
```

### 3. Start the System
```bash
python run.py
```

Open http://localhost:8080 in your browser.

## 💬 Example Queries

### Infrastructure Monitoring
- "Show me the infrastructure health"
- "What's the status of my virtual machines?"
- "Check for any alerts in the system"
- "Show me VM metrics"

### Cost Optimization
- "Analyze my Azure costs"
- "Find unused resources I can delete"
- "Show me rightsizing recommendations"
- "What are my costs by tag Environment"

### Incident Analysis
- "There's a performance issue with the web app"
- "Analyze why the API is slow"
- "The database connection is timing out"

### Deployments
- "List recent deployments"
- "Deploy the sample web app template"
- "Show deployment status"

### Kubernetes/AKS
- "Show me all AKS clusters"
- "What's the status of the production cluster?"
- "Scale the web-app deployment to 5 replicas"
- "Show pod logs for api-server"

### Reports
- "Generate an executive report"
- "Create a cost optimization report"
- "Show me an infrastructure health report"

## 🔧 Configuration

### Model Configuration (config/models.yaml)
Each agent can use a different AI model:
```yaml
agents:
  infrastructure_monitor:
    deployment_name: "gpt-4"
    temperature: 0.3
  cost_optimizer:
    deployment_name: "gpt-35-turbo"
    temperature: 0.2
```

### Agent Configuration (config/agents.yaml)
Enable/disable specific agents:
```yaml
agents:
  - name: InfrastructureMonitor
    enabled: true
  - name: CostOptimizer
    enabled: true
```

## 🏗️ Architecture

### Agents
1. **Infrastructure Monitor** - Real-time Azure resource monitoring
2. **Cost Optimizer** - Cost analysis and optimization recommendations
3. **RCA Analyzer** - AI-powered root cause analysis
4. **Deployment Manager** - ARM template deployments
5. **Report Generator** - Comprehensive reporting with AI insights
6. **Kubernetes Agent** - AKS cluster management

### Key Features
- ✅ Real Azure data integration
- ✅ Different AI models per agent
- ✅ Semantic Kernel orchestration
- ✅ Web chat interface
- ✅ Agent-to-Agent communication
- ✅ Comprehensive logging

## 📊 Sample ARM Deployment

Deploy the included sample web app:
```json
{
  "deployment_config": {
    "name": "test-webapp",
    "resource_group": "devops-sentinel-rg",
    "template_file": "templates/sample-webapp.json",
    "parameters": {
      "webAppName": {"value": "my-test-app"},
      "environment": {"value": "dev"}
    }
  }
}
```

## 🐛 Troubleshooting

### Azure Authentication Issues
```bash
# Login to Azure
az login

# Set default subscription
az account set --subscription "Your Subscription Name"

# Verify
az account show
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Kubernetes Access
```bash
# Get AKS credentials
az aks get-credentials --resource-group myRG --name myAKS

# Verify
kubectl get nodes
```

### Logs
Check `logs/` directory for detailed debugging information.

## 🔐 Security Best Practices

1. **Use Service Principal** instead of CLI auth in production
2. **Store secrets** in Azure Key Vault
3. **Enable RBAC** on all Azure resources
4. **Use managed identities** where possible
5. **Rotate API keys** regularly

## 📚 Advanced Usage

### Custom Reports
Ask: "Create a custom report focusing on security compliance and cost trends"

### Multi-Resource Analysis
Ask: "Compare costs between production and development environments"

### Predictive Analysis
Ask: "Based on current trends, what will our costs be next month?"

### Complex Troubleshooting
Ask: "Analyze the correlation between high CPU usage and increased response times"

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.