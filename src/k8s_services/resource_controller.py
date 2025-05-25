class ResourceController:
    """ResourceController class to manage resources within Kubernetes."""

    def __init__(self, k8s_client):
        self.k8s_client = k8s_client

    def list_resources(self, namespace: str):
        """List all resources in the specified namespace."""
        resources = self.k8s_client.list_namespaced_pod(namespace)
        return resources.items

    def create_resource(self, namespace: str, resource_definition):
        """Create a resource in the specified namespace."""
        return self.k8s_client.create_namespaced_pod(namespace, resource_definition)

    def delete_resource(self, namespace: str, resource_name: str):
        """Delete a resource by name in the specified namespace."""
        return self.k8s_client.delete_namespaced_pod(resource_name, namespace)

    def get_resource(self, namespace: str, resource_name: str):
        """Get details of a specific resource by name in the specified namespace."""
        return self.k8s_client.read_namespaced_pod(resource_name, namespace)

    def update_resource(self, namespace: str, resource_name: str, resource_definition):
        """Update a resource in the specified namespace."""
        return self.k8s_client.patch_namespaced_pod(resource_name, namespace, resource_definition)