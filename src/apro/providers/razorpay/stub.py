"""Deterministic in-memory HTTP transport stub for Razorpay TEST mode testing."""

import json
from typing import Any

import httpx


class DeterministicRazorpayStub(httpx.AsyncBaseTransport):
    """Deterministic, CI-safe HTTP transport stub simulating Razorpay TEST API."""

    def __init__(
        self,
        simulated_status_code: int = 200,
        simulated_body: dict[str, Any] | str | bytes | None = None,
        should_timeout: bool = False,
        should_raise_connection_error: bool = False,
        simulated_latency_seconds: float = 0.0,
    ) -> None:
        self.simulated_status_code = simulated_status_code
        self.simulated_body = simulated_body
        self.should_timeout = should_timeout
        self.should_raise_connection_error = should_raise_connection_error
        self.simulated_latency_seconds = simulated_latency_seconds
        self.recorded_requests: list[dict[str, Any]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle incoming HTTP request deterministically."""
        # 1. Record request for test inspection
        req_record = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "content": request.content.decode("utf-8", errors="replace"),
        }
        self.recorded_requests.append(req_record)

        # 2. Simulate timeout
        if self.should_timeout:
            msg = "Simulated transport timeout connecting to api.razorpay.com"
            raise httpx.ReadTimeout(msg, request=request)

        # 3. Simulate connection error
        if self.should_raise_connection_error:
            msg = "Simulated network connection failure"
            raise httpx.ConnectError(msg, request=request)

        # 4. If explicit simulated body supplied, return it
        if self.simulated_body is not None:
            if isinstance(self.simulated_body, (dict, list)):
                content_bytes = json.dumps(self.simulated_body).encode("utf-8")
                headers = {"content-type": "application/json"}
            elif isinstance(self.simulated_body, str):
                content_bytes = self.simulated_body.encode("utf-8")
                headers = {"content-type": "text/plain"}
            else:
                content_bytes = self.simulated_body
                headers = {"content-type": "application/octet-stream"}

            return httpx.Response(
                status_code=self.simulated_status_code,
                content=content_bytes,
                headers=headers,
                request=request,
            )

        # 5. Default simulated responses based on path
        url_path = request.url.path
        if self.simulated_status_code >= 400:
            err_code = (
                "BAD_REQUEST_ERROR"
                if self.simulated_status_code == 400
                else "GATEWAY_ERROR"
            )
            err_body = {
                "error": {
                    "code": err_code,
                    "description": (
                        f"Simulated error with status {self.simulated_status_code}"
                    ),
                    "source": "gateway",
                    "step": "payment_initiation",
                    "reason": "simulated_rejection",
                }
            }
            return httpx.Response(
                status_code=self.simulated_status_code,
                json=err_body,
                request=request,
            )

        if url_path.endswith("/payment_links") and request.method == "POST":
            try:
                payload = json.loads(request.content)
            except Exception:
                payload = {}

            amount = payload.get("amount", 50000)
            ref_id = payload.get("reference_id", "apro_ref_default")
            import hashlib

            digest = hashlib.sha256(str(ref_id).encode("utf-8")).hexdigest()
            res_payload = {
                "id": f"plink_stub_{digest[:10]}",
                "amount": amount,
                "currency": payload.get("currency", "INR"),
                "status": "created",
                "short_url": f"https://rzp.io/i/stub_{digest[:6]}",
                "description": payload.get("description", "APRO Recovery Link"),
                "created_at": 1725300000,
                "reference_id": ref_id,
                "notes": payload.get("notes", {}),
            }
            return httpx.Response(
                status_code=200,
                json=res_payload,
                request=request,
            )

        if "/notify_by/" in url_path and request.method == "POST":
            return httpx.Response(
                status_code=200,
                json={"success": True},
                request=request,
            )

        # Default fallback response
        return httpx.Response(
            status_code=200,
            json={"status": "ok"},
            request=request,
        )


__all__ = ["DeterministicRazorpayStub"]
