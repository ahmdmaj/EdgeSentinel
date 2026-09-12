import httpx
import logging
from typing import Optional, Dict, Any
from app.config.settings import settings

logger = logging.getLogger("edge.http_client")


class CloudAuthenticationError(Exception):
    """Raised when authentication against the Cloud API fails."""
    pass


class CloudConnectionError(Exception):
    """Raised when the Cloud API is unreachable (network down, outage, timeout)."""
    pass


class CloudApiClient:
    """
    HTTP client for Cloud API communication.
    Manages JWT lifecycle, auto-authentication, and 401 retry resilience.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self.email = email or settings.API_EMAIL
        self.password = password or settings.API_PASSWORD
        self.token: Optional[str] = None

    def _extract_token(self, resp_data: Dict[str, Any]) -> str:
        """Extracts JWT token from standard {'data': {'token': ...}} or fallback format."""
        if isinstance(resp_data, dict):
            if "data" in resp_data and isinstance(resp_data["data"], dict) and "token" in resp_data["data"]:
                return resp_data["data"]["token"]
            if "token" in resp_data:
                return resp_data["token"]
        raise CloudAuthenticationError(f"Unexpected login response payload: {resp_data}")

    # -------------------------------------------------------------------------
    # Async Methods (used by FastAPI main loop)
    # -------------------------------------------------------------------------

    async def login_async(self, timeout: float = 5.0) -> str:
        """Authenticates against the Cloud API asynchronously and caches the JWT."""
        login_url = f"{self.base_url}/api/v1/auth/login"
        payload = {"email": self.email, "password": self.password}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(login_url, json=payload)

                if resp.status_code == 200:
                    token = self._extract_token(resp.json())
                    self.token = token
                    logger.info("Successfully authenticated with Cloud API. JWT cached.")
                    return token
                elif resp.status_code == 401:
                    logger.warning("Cloud API rejected credentials (401 Unauthorized).")
                    raise CloudAuthenticationError("Invalid credentials for Cloud API.")
                else:
                    logger.warning(f"Login failed with status code: {resp.status_code}")
                    raise CloudConnectionError(f"Login failed: HTTP {resp.status_code}")
        except httpx.RequestError as exc:
            logger.warning(f"Cloud API unreachable during login: {exc}")
            raise CloudConnectionError(f"Cloud unreachable: {exc}") from exc

    async def get_token_async(self, force_refresh: bool = False, timeout: float = 5.0) -> str:
        """Returns cached JWT or fetches a new one asynchronously."""
        if not self.token or force_refresh:
            return await self.login_async(timeout=timeout)
        return self.token

    async def post_telemetry_async(self, payload: Dict[str, Any], timeout: float = 5.0) -> httpx.Response:
        """
        Sends telemetry to POST /api/v1/telemetry with Bearer token.
        Resilience Rule: On 401 Unauthorized, automatically re-authenticates and retries once.
        """
        telemetry_url = f"{self.base_url}/api/v1/telemetry"

        # Ensure token is present (falls back to outbox if login fails)
        token = await self.get_token_async(timeout=timeout)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(telemetry_url, json=payload, headers=headers)

                # Resilience: Auto-recover from 401 Unauthorized (expired token or restarted API)
                if resp.status_code == 401:
                    logger.warning("Received 401 Unauthorized on telemetry POST. Re-authenticating and retrying...")
                    self.token = None
                    new_token = await self.login_async(timeout=timeout)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = await client.post(telemetry_url, json=payload, headers=headers)

                return resp
        except httpx.RequestError as exc:
            logger.warning(f"Connection error while transmitting telemetry: {exc}")
            raise CloudConnectionError(f"Cloud unreachable during telemetry POST: {exc}") from exc

    # -------------------------------------------------------------------------
    # Synchronous Methods (used by background outbox sync worker thread)
    # -------------------------------------------------------------------------

    def login_sync(self, timeout: float = 5.0) -> str:
        """Synchronously authenticates against the Cloud API and caches the JWT."""
        login_url = f"{self.base_url}/api/v1/auth/login"
        payload = {"email": self.email, "password": self.password}

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(login_url, json=payload)

                if resp.status_code == 200:
                    token = self._extract_token(resp.json())
                    self.token = token
                    logger.info("Successfully authenticated with Cloud API (sync). JWT cached.")
                    return token
                elif resp.status_code == 401:
                    logger.warning("Cloud API rejected credentials (401 Unauthorized).")
                    raise CloudAuthenticationError("Invalid credentials for Cloud API.")
                else:
                    logger.warning(f"Login failed with status code: {resp.status_code}")
                    raise CloudConnectionError(f"Login failed: HTTP {resp.status_code}")
        except httpx.RequestError as exc:
            logger.warning(f"Cloud API unreachable during sync login: {exc}")
            raise CloudConnectionError(f"Cloud unreachable: {exc}") from exc

    def get_token_sync(self, force_refresh: bool = False, timeout: float = 5.0) -> str:
        """Returns cached JWT or synchronously fetches a new one."""
        if not self.token or force_refresh:
            return self.login_sync(timeout=timeout)
        return self.token

    def post_telemetry_sync(self, payload: Dict[str, Any], timeout: float = 5.0) -> httpx.Response:
        """
        Synchronously sends telemetry to POST /api/v1/telemetry with Bearer token.
        Resilience Rule: On 401 Unauthorized, automatically re-authenticates and retries once.
        """
        telemetry_url = f"{self.base_url}/api/v1/telemetry"

        token = self.get_token_sync(timeout=timeout)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(telemetry_url, json=payload, headers=headers)

                # Resilience: Auto-recover from 401 Unauthorized
                if resp.status_code == 401:
                    logger.warning("Received 401 Unauthorized on sync telemetry POST. Re-authenticating and retrying...")
                    self.token = None
                    new_token = self.login_sync(timeout=timeout)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.post(telemetry_url, json=payload, headers=headers)

                return resp
        except httpx.RequestError as exc:
            logger.warning(f"Connection error while transmitting telemetry (sync): {exc}")
            raise CloudConnectionError(f"Cloud unreachable during telemetry POST: {exc}") from exc


# Shared singleton client instance
cloud_client = CloudApiClient()
