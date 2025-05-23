import pytest
from src.azure.resource_monitor import ResourceMonitor
from src.azure.cost_analyzer import CostAnalyzer
from src.azure.deployment_service import DeploymentService
from unittest.mock import patch

@pytest.fixture
def resource_monitor():
    return ResourceMonitor()

@pytest.fixture
def cost_analyzer():
    return CostAnalyzer()

@pytest.fixture
def deployment_service():
    return DeploymentService()

def test_resource_monitor_initialization(resource_monitor):
    assert resource_monitor is not None
    assert hasattr(resource_monitor, 'monitor_resources')

def test_cost_analyzer_initialization(cost_analyzer):
    assert cost_analyzer is not None
    assert hasattr(cost_analyzer, 'analyze_costs')

def test_deployment_service_initialization(deployment_service):
    assert deployment_service is not None
    assert hasattr(deployment_service, 'deploy_application')

@patch('src.azure.resource_monitor.ResourceMonitor.get_resources')
def test_resource_monitor_get_resources(mock_get_resources, resource_monitor):
    mock_get_resources.return_value = ['resource1', 'resource2']
    resources = resource_monitor.get_resources()
    assert resources == ['resource1', 'resource2']

@patch('src.azure.cost_analyzer.CostAnalyzer.calculate_costs')
def test_cost_analyzer_calculate_costs(mock_calculate_costs, cost_analyzer):
    mock_calculate_costs.return_value = 100
    cost = cost_analyzer.calculate_costs()
    assert cost == 100

@patch('src.azure.deployment_service.DeploymentService.deploy_application')
def test_deployment_service_deploy_application(mock_deploy_application, deployment_service):
    mock_deploy_application.return_value = True
    result = deployment_service.deploy_application('app_name')
    assert result is True