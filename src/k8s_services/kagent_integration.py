from kagent import KAgent  # Assuming KAgent is the main class from the kagent repository

class KAgentIntegration:
    def __init__(self, kube_config_path: str):
        self.kube_config_path = kube_config_path
        self.kagent = KAgent(config_path=self.kube_config_path)

    def deploy_application(self, app_name: str, image: str, replicas: int):
        """Deploy an application to the Kubernetes cluster."""
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": app_name
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": app_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": app_name
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": app_name,
                                "image": image
                            }
                        ]
                    }
                }
            }
        }
        return self.kagent.create_deployment(deployment)

    def monitor_resources(self):
        """Monitor resources in the Kubernetes cluster."""
        return self.kagent.get_resources()

    def perform_rollback(self, app_name: str):
        """Rollback the last deployment of the specified application."""
        return self.kagent.rollback_deployment(app_name)

    def get_pod_logs(self, pod_name: str):
        """Retrieve logs from a specific pod."""
        return self.kagent.get_logs(pod_name)

    def scale_application(self, app_name: str, replicas: int):
        """Scale the number of replicas for a given application."""
        return self.kagent.scale_deployment(app_name, replicas)