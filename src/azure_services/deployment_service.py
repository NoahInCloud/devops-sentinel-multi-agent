class DeploymentService:
    def __init__(self, azure_client):
        self.azure_client = azure_client

    def deploy_application(self, app_name, resource_group, deployment_template, parameters):
        deployment_properties = {
            'mode': 'Incremental',
            'template': deployment_template,
            'parameters': parameters
        }
        deployment = self.azure_client.deployments.begin_create_or_update(
            resource_group,
            app_name,
            deployment_properties
        )
        return deployment.result()

    def update_application(self, app_name, resource_group, deployment_template, parameters):
        deployment_properties = {
            'mode': 'Incremental',
            'template': deployment_template,
            'parameters': parameters
        }
        deployment = self.azure_client.deployments.begin_create_or_update(
            resource_group,
            app_name,
            deployment_properties
        )
        return deployment.result()

    def delete_application(self, app_name, resource_group):
        delete_operation = self.azure_client.deployments.begin_delete(resource_group, app_name)
        return delete_operation.result()

    def get_deployment_status(self, app_name, resource_group):
        deployment = self.azure_client.deployments.get(resource_group, app_name)
        return deployment.properties.provisioning_state

    def list_deployments(self, resource_group):
        deployments = self.azure_client.deployments.list(resource_group)
        return [deployment.name for deployment in deployments]