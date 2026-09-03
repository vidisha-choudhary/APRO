"""Async HTTP transport client for Razorpay TEST mode API."""

import logging
from typing import Any

import httpx

from apro.providers.exceptions import (
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.errors import classify_razorpay_error
from apro.providers.razorpay.models import (
    RazorpayNotifyRequest,
    RazorpayNotifyResponse,
    RazorpayPaymentLinkRequest,
    RazorpayPaymentLinkResponse,
)
from apro.providers.razorpay.security import sanitize_dict

logger = logging.getLogger("apro.providers.razorpay.client")


class RazorpayTestModeClient:
    """Outbound async HTTP client communicating with Razorpay TEST mode API."""

    def __init__(
        self,
        config: RazorpayTestModeConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._secrets = config.get_secret_set()
        self._auth = (config.key_id, config.key_secret)
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                auth=self._auth,
                timeout=self.config.timeout_seconds,
                transport=self._transport,
                headers={"User-Agent": "APRO-Execution-Engine/1.0"},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "RazorpayTestModeClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def create_payment_link(
        self,
        request: RazorpayPaymentLinkRequest,
    ) -> RazorpayPaymentLinkResponse:
        """Execute POST /v1/payment_links in Razorpay TEST mode."""
        client = self._get_client()
        url = "/v1/payment_links"
        payload = request.model_dump(exclude_none=True)

        logger.debug(
            "Dispatching Razorpay Payment Link request to %s: %s",
            url,
            sanitize_dict(payload, self._secrets),
        )

        try:
            response = await client.post(url, json=payload)
        except httpx.TimeoutException as e:
            msg = (
                f"Razorpay Payment Link creation timed out after "
                f"{self.config.timeout_seconds}s"
            )
            raise ProviderTimeoutError(msg) from e
        except httpx.RequestError as e:
            msg = f"Network transport failure connecting to Razorpay: {e}"
            raise ProviderUnavailableError(msg) from e

        if response.status_code >= 400:
            raise classify_razorpay_error(
                response.status_code, response.content, self._secrets
            )

        try:
            data = response.json()
            return RazorpayPaymentLinkResponse(**data)
        except Exception as e:
            msg = f"Malformed JSON or unexpected schema in Razorpay response: {e}"
            raise ProviderMalformedResponseError(msg) from e

    async def notify_payment_link(
        self,
        request: RazorpayNotifyRequest,
    ) -> RazorpayNotifyResponse:
        """Execute POST /v1/payment_links/{id}/notify_by/{medium} in TEST mode."""
        client = self._get_client()
        url = f"/v1/payment_links/{request.payment_link_id}/notify_by/{request.medium}"

        logger.debug(
            "Dispatching Razorpay Payment Link notification request to %s",
            url,
        )

        try:
            response = await client.post(url, json={})
        except httpx.TimeoutException as e:
            msg = (
                f"Razorpay notification request timed out after "
                f"{self.config.timeout_seconds}s"
            )
            raise ProviderTimeoutError(msg) from e
        except httpx.RequestError as e:
            msg = f"Network transport failure connecting to Razorpay: {e}"
            raise ProviderUnavailableError(msg) from e

        if response.status_code >= 400:
            raise classify_razorpay_error(
                response.status_code, response.content, self._secrets
            )

        try:
            data = response.json()
            return RazorpayNotifyResponse(**data)
        except Exception as e:
            msg = f"Malformed JSON in Razorpay notification response: {e}"
            raise ProviderMalformedResponseError(msg) from e


__all__ = ["RazorpayTestModeClient"]
