"""Client for the unofficial FLO eMobility cloud API."""

import base64
from collections.abc import Mapping
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp

from .const import API_BASE_URL, API_VERSIONS, CLIENT_ID, IDP_BASE_URL, LOGGER


class FloX3Error(Exception):
    """Base exception for FLO X3 API errors."""


class FloX3AuthError(FloX3Error):
    """Authentication failed or requires an unsupported interaction."""


class FloX3ApiError(FloX3Error):
    """An API request failed."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.status = status


class FloX3NoStationsError(FloX3ApiError):
    """The authenticated FLO account has no compatible stations."""


class FloX3ApiClient:
    """Authenticate and retrieve read-only FLO charger data."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        api_version: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self.api_version = api_version
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at = 0.0

    async def async_get_stations(self) -> tuple[list[dict[str, Any]], str]:
        """Get the account's stations, trying supported API versions."""
        for version in (self.api_version,) if self.api_version else API_VERSIONS:
            try:
                stations = await self._async_api_get(f"/{version}/user/stations")
            except FloX3ApiError as err:
                if err.status == 404 and self.api_version is None:
                    LOGGER.debug("FLO API %s is unavailable; trying fallback", version)
                    continue
                raise

            if not isinstance(stations, list):
                raise FloX3ApiError("FLO returned an unexpected stations response")

            valid_stations = [
                station
                for station in stations
                if isinstance(station, dict)
                and isinstance(station.get("information"), dict)
                and station["information"].get("id")
                and station["information"].get("name")
            ]
            if valid_stations:
                self.api_version = version
                return valid_stations, version

        raise FloX3NoStationsError(
            "No FLO stations were returned. The X3 API version may not be compatible."
        )

    async def async_get_charger_data(
        self, station_id: str
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Get station and current session data."""
        if self.api_version is None:
            raise FloX3ApiError("FLO API version has not been selected")

        stations = await self._async_api_get(f"/{self.api_version}/user/stations")
        if not isinstance(stations, list):
            raise FloX3ApiError("FLO returned an unexpected stations response")

        station = next(
            (
                item
                for item in stations
                if isinstance(item, dict)
                and isinstance(item.get("information"), dict)
                and item["information"].get("id") == station_id
            ),
            None,
        )
        if station is None:
            raise FloX3ApiError("The configured FLO station was not found")

        try:
            sessions = await self._async_api_get(f"/{self.api_version}/user/sessions")
        except FloX3ApiError as err:
            if err.status != 404:
                raise
            if self.api_version != "v3.1":
                return station, None
            try:
                sessions = await self._async_api_get("/v3.0/user/sessions")
            except FloX3ApiError as fallback_err:
                if fallback_err.status != 404:
                    raise
                return station, None
        if not isinstance(sessions, list):
            raise FloX3ApiError("FLO returned an unexpected sessions response")

        matching_sessions = [
            item
            for item in sessions
            if isinstance(item, dict)
            and isinstance(item.get("station"), dict)
            and item["station"].get("id") == station_id
        ]
        session = next(
            (
                item
                for item in matching_sessions
                if item.get("sessionState") in {"Charging", "NotCharging"}
            ),
            matching_sessions[0] if matching_sessions else None,
        )
        return station, session

    async def _async_api_get(self, path: str) -> Any:
        """Make an authenticated API GET request."""
        token = await self._async_get_access_token()
        async with self._session.get(
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
        ) as response:
            if response.status == 401:
                self._access_token = None
                token = await self._async_get_access_token(force=True)
                async with self._session.get(
                    f"{API_BASE_URL}{path}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
                ) as retry_response:
                    try:
                        return await self._async_read_response(retry_response)
                    except FloX3ApiError as err:
                        if err.status == 401:
                            raise FloX3AuthError(
                                "FLO rejected the refreshed access token"
                            ) from err
                        raise
            return await self._async_read_response(response)

    async def _async_get_access_token(self, *, force: bool = False) -> str:
        """Get an access token, refreshing or authenticating as needed."""
        if force:
            self._access_token = None
            self._token_expires_at = 0

        if (
            not force
            and self._access_token is not None
            and time.monotonic() < self._token_expires_at
        ):
            return self._access_token

        if self._refresh_token is not None:
            try:
                await self._async_refresh_token()
            except FloX3AuthError:
                LOGGER.debug("FLO refresh token expired; starting a new login")
                self._access_token = None
                self._refresh_token = None

        if self._access_token is None or time.monotonic() >= self._token_expires_at:
            await self._async_login()

        if self._access_token is None:
            raise FloX3AuthError("FLO authentication did not return an access token")
        return self._access_token

    async def _async_refresh_token(self) -> None:
        """Refresh the access token."""
        async with self._session.post(
            f"{IDP_BASE_URL}/token",
            headers={"Accept": "*/*"},
            data={
                "refresh_token": self._refresh_token,
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
            },
        ) as response:
            data = await self._async_read_auth_response(response)
        self._store_tokens(data)

    async def _async_login(self) -> None:
        """Run FLO's observed PingOne PKCE username/password flow."""
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )

        async with self._session.post(
            f"{IDP_BASE_URL}/authorize",
            headers={"Accept": "*/*"},
            data={
                "client_id": CLIENT_ID,
                "response_mode": "pi.flow",
                "response_type": "code",
                "scope": "eMobility:all",
                "code_challenge_method": "S256",
                "code_challenge": challenge,
            },
        ) as response:
            authorize_data = await self._async_read_auth_response(response)

        if authorize_data.get("status") != "USERNAME_PASSWORD_REQUIRED":
            raise FloX3AuthError("FLO requires an unsupported sign-in step")

        links = authorize_data.get("_links")
        credentials_link = (
            links.get("usernamePassword.check") if isinstance(links, dict) else None
        )
        if not isinstance(credentials_link, dict) or not isinstance(
            credentials_link.get("href"), str
        ):
            raise FloX3AuthError("FLO sign-in response did not include a login link")

        async with self._session.post(
            self._async_idp_url(credentials_link["href"]),
            headers={
                "Accept": "*/*",
                "Content-Type": "application/vnd.pingidentity.usernamePassword.check+json",
            },
            json={"username": self._username, "password": self._password},
        ) as response:
            credentials_data = await self._async_read_auth_response(response)

        if credentials_data.get("status") != "COMPLETED":
            raise FloX3AuthError("FLO credentials were rejected or require MFA")

        resume_url = credentials_data.get("resumeUrl")
        if not isinstance(resume_url, str):
            raise FloX3AuthError("FLO sign-in response did not include a resume URL")

        async with self._session.get(
            self._async_idp_url(resume_url),
            headers={"Accept": "*/*"},
        ) as response:
            resume_data = await self._async_read_auth_response(response)

        authorize_response = resume_data.get("authorizeResponse")
        code = (
            authorize_response.get("code")
            if isinstance(authorize_response, dict)
            else None
        )
        if resume_data.get("status") != "COMPLETED" or not isinstance(code, str):
            raise FloX3AuthError("FLO sign-in did not complete")

        async with self._session.post(
            f"{IDP_BASE_URL}/token",
            headers={"Accept": "*/*"},
            data={
                "code": code,
                "code_verifier": verifier,
                "client_id": CLIENT_ID,
                "grant_type": "authorization_code",
            },
        ) as response:
            token_data = await self._async_read_auth_response(response)
        self._store_tokens(token_data)

    def _async_idp_url(self, href: str) -> str:
        """Resolve a PingOne link without allowing an unexpected host."""
        url = urljoin(f"{IDP_BASE_URL}/", href)
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "auth.pingone.ca":
            raise FloX3AuthError("FLO returned an unexpected authentication URL")
        return url

    async def _async_read_response(self, response: aiohttp.ClientResponse) -> Any:
        """Parse an API response."""
        if response.status >= 400:
            raise FloX3ApiError(
                f"FLO API request failed with HTTP {response.status}",
                status=response.status,
            )
        try:
            return await response.json()
        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise FloX3ApiError("FLO API returned invalid JSON") from err

    async def _async_read_auth_response(
        self, response: aiohttp.ClientResponse
    ) -> dict[str, Any]:
        """Parse an authentication response."""
        if response.status >= 400:
            raise FloX3AuthError(
                f"FLO authentication failed with HTTP {response.status}"
            )
        try:
            data = await response.json()
        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
            raise FloX3AuthError("FLO authentication returned invalid JSON") from err
        if not isinstance(data, dict):
            raise FloX3AuthError("FLO authentication returned an invalid response")
        return data

    def _store_tokens(self, data: Mapping[str, Any]) -> None:
        """Store returned tokens in memory only."""
        access_token = data.get("access_token")
        expires_in = data.get("expires_in")
        refresh_token = data.get("refresh_token")
        if (
            not isinstance(access_token, str)
            or not isinstance(expires_in, (int, float))
            or expires_in <= 0
        ):
            raise FloX3AuthError("FLO authentication returned invalid token data")
        self._access_token = access_token
        self._refresh_token = refresh_token if isinstance(refresh_token, str) else None
        self._token_expires_at = time.monotonic() + expires_in
