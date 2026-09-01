"""Script to simulate a Razorpay payment.failed webhook delivery locally."""

import argparse
import hashlib
import hmac
import json
import sys

import httpx

# Mock payload based on standard Razorpay structure
MOCK_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_mock_123",
    "event": "payment.failed",
    "contains": ["payment"],
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_mock_999",
                "entity": "payment",
                "amount": 25000,
                "currency": "INR",
                "status": "failed",
                "order_id": "order_mock_999",
                "invoice_id": None,
                "international": False,
                "method": "upi",
                "amount_refunded": 0,
                "refund_status": None,
                "captured": False,
                "description": "UPI payment failure simulation",
                "bank": None,
                "wallet": None,
                "vpa": "success@upi",
                "email": "customer@example.com",
                "contact": "+919999999999",
                "notes": [],
                "fee": None,
                "tax": None,
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment failed at bank gateway.",
                "error_source": "gateway",
                "error_step": "payment_processing",
                "error_reason": "payment_failed_at_gateway",
                "created_at": 1672531200,
            }
        }
    },
    "created_at": 1672531200,
}


def simulate(url: str, secret: str, event_id: str, mutate: bool = False) -> None:
    """Send a signed webhook to the target APRO instance."""
    body = json.dumps(MOCK_PAYLOAD).encode("utf-8")

    # If mutation is requested, modify the payload slightly after signature generation
    if mutate:
        sig_body = body
        payload_mutated = MOCK_PAYLOAD.copy()
        payload_mutated["payload"]["payment"]["entity"]["amount"] = 30000
        body = json.dumps(payload_mutated).encode("utf-8")
    else:
        sig_body = body

    signature = hmac.new(secret.encode("utf-8"), sig_body, hashlib.sha256).hexdigest()

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    print(f"Sending request to {url}...")
    print(f"Event ID: {event_id}")
    print(f"Signature: {signature}")
    if mutate:
        print("Note: Body has been mutated after signature generation.")

    try:
        response = httpx.post(url, content=body, headers=headers, timeout=5.0)
        print(f"\nResponse Status: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"\nError sending webhook: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Razorpay webhook locally.")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/webhooks/razorpay",
        help="APRO webhook URL",
    )
    parser.add_argument(
        "--secret", default="test_webhook_secret", help="Webhook secret"
    )
    parser.add_argument("--event-id", default="evt_mock_999", help="Razorpay Event ID")
    parser.add_argument(
        "--mutate",
        action="store_true",
        help="Mutate body to verify signature failure",
    )

    args = parser.parse_args()
    simulate(args.url, args.secret, args.event_id, args.mutate)
