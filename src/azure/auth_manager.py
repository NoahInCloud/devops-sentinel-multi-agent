class AuthManager:
    """Handles authentication with Azure services."""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.token = None

    async def authenticate(self):
        """Authenticate with Azure and retrieve an access token."""
        # Logic to authenticate and retrieve the token
        # This is a placeholder for the actual implementation
        self.token = await self._get_access_token()

    async def _get_access_token(self):
        """Internal method to get access token from Azure."""
        # Placeholder for token retrieval logic
        return "access_token"

    def get_token(self) -> str:
        """Return the current access token."""
        if not self.token:
            raise Exception("Authentication required. Please call authenticate() first.")
        return self.token