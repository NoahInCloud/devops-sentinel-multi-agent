import unittest
from src.agents.infrastructure_monitor import InfrastructureMonitor
from src.agents.rca_analyzer import RCAAnalyzer
from src.agents.cost_optimizer import CostOptimizer
from src.agents.report_generator import ReportGenerator
from src.agents.deployment_manager import DeploymentManager
from src.agents.kubernetes_agent import KubernetesAgent

class TestAgents(unittest.TestCase):

    def setUp(self):
        self.infrastructure_monitor = InfrastructureMonitor()
        self.rca_analyzer = RCAAnalyzer()
        self.cost_optimizer = CostOptimizer()
        self.report_generator = ReportGenerator()
        self.deployment_manager = DeploymentManager()
        self.kubernetes_agent = KubernetesAgent()

    def test_infrastructure_monitor(self):
        # Test monitoring functionality
        result = self.infrastructure_monitor.monitor()
        self.assertIsNotNone(result)

    def test_rca_analyzer(self):
        # Test root cause analysis functionality
        issues = ["issue1", "issue2"]
        analysis = self.rca_analyzer.analyze(issues)
        self.assertIsInstance(analysis, dict)

    def test_cost_optimizer(self):
        # Test cost optimization functionality
        costs = {"service1": 100, "service2": 200}
        optimized_costs = self.cost_optimizer.optimize(costs)
        self.assertLessEqual(sum(optimized_costs.values()), sum(costs.values()))

    def test_report_generator(self):
        # Test report generation functionality
        data = {"metric1": 10, "metric2": 20}
        report = self.report_generator.generate(data)
        self.assertIn("Report", report)

    def test_deployment_manager(self):
        # Test deployment functionality
        deployment_result = self.deployment_manager.deploy("app_name")
        self.assertTrue(deployment_result)

    def test_kubernetes_agent(self):
        # Test Kubernetes agent functionality
        k8s_status = self.kubernetes_agent.get_status()
        self.assertIsNotNone(k8s_status)

if __name__ == '__main__':
    unittest.main()