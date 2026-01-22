import os
from quickbooks import QuickBooks
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes


class QuickBooksClient:
    def __init__(self):
        self.client_id = os.getenv("QB_CLIENT_ID")
        self.client_secret = os.getenv("QB_CLIENT_SECRET")
        self.redirect_uri = os.getenv("QB_REDIRECT_URI")
        self.environment = os.getenv("QB_ENVIRONMENT", "sandbox")  # Default to sandbox

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError(
                "QuickBooks environment variables (QB_CLIENT_ID, QB_CLIENT_SECRET, QB_REDIRECT_URI) "
                "must be set."
            )

    def get_auth_client(self, access_token=None, refresh_token=None, realm_id=None):
        """Returns an AuthClient instance."""
        return AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            environment=self.environment,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def get_auth_url(self, csrf_token: str) -> str:
        """Generates the authorization URL for QuickBooks Online."""
        auth_client = self.get_auth_client()
        return auth_client.get_authorization_url([Scopes.ACCOUNTING], state_token=csrf_token)

    def get_quickbooks_client(self, realm_id: str, access_token: str, refresh_token: str):
        """Returns an authorized QuickBooks client instance."""
        auth_client = self.get_auth_client(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        return QuickBooks(
            auth_client=auth_client,
            company_id=realm_id,
            minorversion=65,  # Latest stable minor version
        )
