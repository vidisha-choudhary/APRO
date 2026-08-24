\# APRO — Razorpay Capability Map



\## 1. Purpose



This document records the Razorpay capabilities that APRO can rely on for its implementation and demonstration.



The objective is to distinguish:



\* capabilities available directly through Razorpay,

\* capabilities that can be demonstrated in Razorpay Test Mode,

\* capabilities that must be simulated,

\* and capabilities implemented entirely by APRO.



\---



\## 2. Razorpay Test Mode



Razorpay provides Test Mode for testing payment flows without using real money.



Test Mode transactions can generate webhook events, and Razorpay states that the webhook payload structure remains consistent between Test and Live environments.



Therefore APRO will use Test Mode for safe integration demonstrations.



\---



\## 3. Payment Webhooks



Relevant payment webhook events include:



\* `payment.authorized`

\* `payment.captured`

\* `payment.failed`



Payment webhook payloads provide information including:



\* payment ID,

\* amount,

\* status,

\* order ID,

\* payment method,

\* error code,

\* error description,

\* error source,

\* error step,

\* error reason,

\* timestamps,

\* and other payment metadata.



These fields will form the primary input to APRO's diagnosis and state-management systems.



Source:



https://razorpay.com/docs/webhooks/payments/



\---



\## 4. Failed → Captured State Transition



Razorpay documents that a `payment.failed` webhook may be followed by a `payment.captured` webhook for the same transaction.



This can occur when a customer successfully retries after an initial failure.



APRO must therefore treat payment recovery as a state-aware process.



Before executing a recovery action, APRO must verify that the payment remains eligible for recovery.



If the payment has already been captured:



\*\*STOP\*\*



Source:



https://razorpay.com/docs/webhooks/payments/



\---



\## 5. Orders



Razorpay Orders are associated with payments and help prevent multiple payments against the same order.



`order.paid` is emitted when the associated payment is captured.



APRO will maintain awareness of the relationship:



\*\*Order → Payment → Recovery Case\*\*



Source:



https://razorpay.com/docs/webhooks/orders/



\---



\## 6. Payment APIs



Razorpay Payment APIs support retrieving payment information and changing an authorized payment to captured.



They are not a generic API for directly collecting a payment.



Therefore APRO must not assume the existence of an unrestricted `retry\_payment()` API.



Source:



https://razorpay.com/docs/api/payments/



\---



\## 7. Payment Links



Razorpay provides Payment Link APIs that allow applications to:



\* create Payment Links,

\* fetch Payment Links,

\* update Payment Links,

\* cancel Payment Links,

\* resend notifications.



The standard Payment Link endpoint is:



`POST /v1/payment\_links`



Payment Links can be tested in Razorpay Test Mode.



Source:



https://razorpay.com/docs/api/payments/payment-links/



\---



\## 8. Payment Link Test Flow



Razorpay provides a Test Mode workflow in which a Payment Link can be opened and a test payment can be completed using a selected success or failure outcome.



This provides APRO with a genuine testable recovery mechanism.



Potential flow:



```text

Payment Failure

&#x20;     ↓

APRO Decision

&#x20;     ↓

Payment Link Approved

&#x20;     ↓

Create Payment Link

&#x20;     ↓

Test Payment

&#x20;     ↓

Payment / Payment-Link Webhook

&#x20;     ↓

Revenue Recovered

```



Source:



https://razorpay.com/docs/payments/payment-links/create/



\---



\## 9. Payment Link Test Limitation



Razorpay currently documents a limit of 30 Payment Links per business in Test Mode unless additional capacity is requested from Razorpay Support.



Therefore Payment Links cannot be used as the sole mechanism for large-scale benchmark evaluation.



Source:



https://razorpay.com/docs/api/payments/payment-links/create-standard/



\---



\## 10. Payment Link Webhooks



Razorpay provides Payment Link webhook events including:



`payment\_link.paid`



These events contain payment-link, order and payment information.



Source:



https://razorpay.com/docs/webhooks/payment-links/



\---



\## 11. Capability Classification



| Capability                 | Availability       | APRO Usage                  |

| -------------------------- | ------------------ | --------------------------- |

| Payment events             | Razorpay Test Mode | Real integration            |

| Payment failures           | Razorpay Test Mode | Real + simulated            |

| Payment captures           | Razorpay Test Mode | Real + simulated            |

| Failure metadata           | Razorpay           | Diagnosis                   |

| Payment state changes      | Razorpay webhooks  | State engine                |

| Failed → Captured sequence | Razorpay           | Safety demonstration        |

| Payment retrieval          | Razorpay API       | State verification          |

| Payment capture            | Razorpay API       | Limited test workflow       |

| Payment Links              | Razorpay API       | Real recovery demonstration |

| Payment Link paid event    | Razorpay webhook   | Recovery confirmation       |

| Retry decisioning          | APRO               | AI/ML decision              |

| Customer outreach          | APRO               | Simulated initially         |

| Escalation                 | APRO               | Internal workflow           |

| Stop                       | APRO               | Internal workflow           |

| Large-scale benchmark      | APRO simulator     | Synthetic                   |

| Recovery-value estimation  | APRO               | AI/ML                       |

| Policy enforcement         | APRO               | Deterministic               |

| Audit trail                | APRO               | Deterministic               |



\---



\## 12. Two Evaluation Environments



APRO will use two environments.



\### Environment A — Razorpay Test Mode



Purpose:



\* prove real Razorpay integration,

\* receive genuine webhook events,

\* demonstrate real Payment Link recovery,

\* demonstrate state transitions,

\* validate integration behavior.



\### Environment B — APRO Simulation



Purpose:



\* generate large batches,

\* test thousands of cases,

\* evaluate recovery strategies,

\* compare baselines,

\* measure economic performance.



Both environments will use the same internal canonical payment-event model and the same decision engine.



\---



\## 13. Canonical Event Boundary



APRO will not allow the decision engine to depend directly on Razorpay-specific payload structures.



Instead:



```text

Razorpay Webhook

&#x20;      ↓

Razorpay Adapter

&#x20;      ↓

Canonical Payment Event

&#x20;      ↓

APRO Decision Engine

```



The simulator will use the same canonical model:



```text

Synthetic Event

&#x20;      ↓

Simulation Adapter

&#x20;      ↓

Canonical Payment Event

&#x20;      ↓

APRO Decision Engine

```



This ensures that the decision engine can be evaluated independently of the external payment provider.



\---



\## 14. Real vs Simulated Claims



The project must clearly distinguish between:



\### Real Razorpay Test Mode



Used to demonstrate integration and executable workflows.



\### Synthetic Simulation



Used to measure large-scale recovery performance.



Synthetic results must never be presented as actual Razorpay merchant revenue.



\---



\## 15. Current Implementation Strategy



APRO will prioritize capabilities in this order:



1\. Canonical payment-event model

2\. Payment state management

3\. Failure diagnosis

4\. Recovery decisioning

5\. Policy enforcement

6\. Simulation

7\. Economic benchmark

8\. Razorpay Test Mode integration

9\. Real Payment Link recovery demonstration

10\. Dashboard and presentation



\---



\## 16. Important Constraint



APRO must not invent or assume Razorpay APIs.



Before implementing any recovery action against Razorpay, the current official Razorpay API documentation must be checked.



If a capability is unavailable directly through Razorpay, APRO will either:



\* implement an alternative supported workflow,

\* simulate the capability,

\* or explicitly document the limitation.



\---



\## 17. Source References



Razorpay Payments Webhooks:



https://razorpay.com/docs/webhooks/payments/



Razorpay Webhook Validation and Testing:



https://razorpay.com/docs/webhooks/validate-test/



Razorpay Payments APIs:



https://razorpay.com/docs/api/payments/



Razorpay Payment Link APIs:



https://razorpay.com/docs/api/payments/payment-links/



Razorpay Payment Link Test Flow:



https://razorpay.com/docs/payments/payment-links/create/



Razorpay Orders Webhooks:



https://razorpay.com/docs/webhooks/orders/



