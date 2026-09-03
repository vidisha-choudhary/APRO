"""Provider-specific request and response models for Razorpay TEST mode."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RazorpayPaymentLinkCustomer(BaseModel):
    """Customer contact details attached to a Razorpay Payment Link."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str | None = None
    email: str | None = None
    contact: str | None = None


class RazorpayPaymentLinkNotify(BaseModel):
    """Notification dispatch options for a Razorpay Payment Link."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sms: bool = True
    email: bool = True


class RazorpayPaymentLinkRequest(BaseModel):
    """Request payload sent to POST /v1/payment_links."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: int = Field(gt=0, description="Amount in currency subunits (paise)")
    currency: str = Field(default="INR")
    accept_partial: bool = Field(default=False)
    description: str = Field(description="Description of payment link purpose")
    customer: RazorpayPaymentLinkCustomer | None = None
    notify: RazorpayPaymentLinkNotify | None = None
    reminder_enable: bool = False
    notes: dict[str, str] = Field(default_factory=dict)
    expire_by: int | None = None
    reference_id: str | None = Field(
        default=None,
        description="Deterministic idempotency / execution reference",
    )


class RazorpayPaymentLinkResponse(BaseModel):
    """Response payload returned by POST /v1/payment_links."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(description="Unique Razorpay Payment Link ID (plink_...)")
    amount: int
    currency: str = "INR"
    status: str = Field(description="e.g. created, paid, cancelled, expired")
    short_url: str | None = None
    description: str | None = None
    customer: dict[str, Any] | None = None
    created_at: int | None = None
    reference_id: str | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


class RazorpayNotifyRequest(BaseModel):
    """Request payload for POST /v1/payment_links/{id}/notify_by/{medium}."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    payment_link_id: str
    medium: str = Field(description="sms or email")


class RazorpayNotifyResponse(BaseModel):
    """Response payload returned by payment link notification endpoint."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    success: bool = True


class RazorpayErrorDetail(BaseModel):
    """Standard Razorpay error body structure."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    code: str
    description: str
    source: str | None = None
    step: str | None = None
    reason: str | None = None
    field: str | None = None


class RazorpayErrorResponse(BaseModel):
    """Top-level Razorpay error wrapper."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    error: RazorpayErrorDetail


__all__ = [
    "RazorpayErrorDetail",
    "RazorpayErrorResponse",
    "RazorpayNotifyRequest",
    "RazorpayNotifyResponse",
    "RazorpayPaymentLinkCustomer",
    "RazorpayPaymentLinkNotify",
    "RazorpayPaymentLinkRequest",
    "RazorpayPaymentLinkResponse",
]
