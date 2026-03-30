"""Klara API authentication as httpx.Auth for transparent token management."""

import os
import time
import httpx


API_BASE = "https://api.klara.ch"


class KlaraAuth(httpx.Auth):
    """httpx Auth handler with automatic tenant discovery, token generation, and refresh."""

    requires_response_body = True

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.tenant_id: str | None = None
        self.company_id: str | None = None
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.token_expires_at: float = 0
        self.refresh_expires_at: float = 0
        self._token_client = httpx.AsyncClient(base_url=API_BASE, timeout=30)

    async def async_auth_flow(self, request):
        await self._ensure_authenticated()
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        response = yield request

        if response.status_code == 401:
            self.access_token = None
            await self._ensure_authenticated()
            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request

    async def _ensure_authenticated(self) -> None:
        if self.access_token and time.time() < self.token_expires_at - 60:
            return
        if self.refresh_token and time.time() < self.refresh_expires_at - 60:
            await self._refresh()
            return
        await self._full_login()

    async def _full_login(self) -> None:
        if not self.tenant_id or not self.company_id:
            resp = await self._token_client.post(
                "/core/latest/tenants",
                data={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            tenants = resp.json()
            if not tenants:
                raise RuntimeError("No tenants found for this user")
            # Pick tenant by KLARA_TENANT env var (company_name match), default to personal (company_id=0)
            target = os.environ.get("KLARA_TENANT", "")
            tenant = next(
                (t for t in tenants if target and target.lower() in t.get("company_name", "").lower()),
                next((t for t in tenants if t.get("company_id") == 0), tenants[0]),
            )
            self.tenant_id = str(tenant["tenant_id"])
            self.company_id = str(tenant["company_id"])

        resp = await self._token_client.post(
            "/core/latest/token",
            data={
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
                "tenant_id": self.tenant_id,
                "company_id": self.company_id,
            },
        )
        resp.raise_for_status()
        self._store_tokens(resp.json())

    async def _refresh(self) -> None:
        resp = await self._token_client.post(
            "/core/latest/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        if resp.status_code != 200:
            self.refresh_token = None
            await self._full_login()
            return
        self._store_tokens(resp.json())

    def _store_tokens(self, data: dict) -> None:
        now = time.time()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refreshToken")
        self.token_expires_at = now + data.get("expires_in", 300)
        self.refresh_expires_at = now + data.get("refresh_expires_in", 1800)

    async def close(self) -> None:
        await self._client.aclose()
