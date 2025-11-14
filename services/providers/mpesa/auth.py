"""
M-Pesa Daraja API Authentication
Handles access token generation for M-Pesa API requests
"""

import os
import base64
import requests
from typing import Optional
from flask import current_app


class MpesaAuth:
    """Handles M-Pesa Daraja API authentication"""

    def __init__(self):
        self.consumer_key = os.environ.get("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")
        self.base_url = os.environ.get(
            "MPESA_BASE_URL", "https://sandbox.safaricom.co.ke"
        )
        self._access_token = None
        self._token_expires_at = None

    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get or refresh M-Pesa access token
        
        Args:
            force_refresh: If True, force a new token request even if cached
            
        Returns:
            Access token string or None if authentication fails
        """
        # Return cached token if available and not forcing refresh
        if not force_refresh and self._access_token and self._token_expires_at:
            import time
            if time.time() < self._token_expires_at:
                return self._access_token

        if not self.consumer_key or not self.consumer_secret:
            current_app.logger.error(
                "M-Pesa credentials not configured: MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET required"
            )
            return None

        # Generate base64 encoded credentials
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Request access token
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        headers = {"Authorization": f"Basic {encoded_credentials}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)  # Default to 1 hour

            if access_token:
                self._access_token = access_token
                import time
                # Set expiration time (subtract 60 seconds buffer)
                self._token_expires_at = time.time() + expires_in - 60
                current_app.logger.info("M-Pesa access token obtained successfully")
                return access_token
            else:
                current_app.logger.error(
                    f"M-Pesa auth failed: {data.get('error_description', 'Unknown error')}"
                )
                return None

        except requests.exceptions.RequestException as e:
            current_app.logger.exception(f"Failed to get M-Pesa access token: {e}")
            return None
        except Exception as e:
            current_app.logger.exception(f"Unexpected error during M-Pesa auth: {e}")
            return None

    def is_authenticated(self) -> bool:
        """Check if we have a valid access token"""
        return self.get_access_token() is not None

