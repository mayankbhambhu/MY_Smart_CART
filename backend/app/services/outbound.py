"""Outbound HTTP to third parties (Razorpay, SMS gateways).

Kept in one place so tests can swap `client` for one backed by a mock transport."""

import httpx2

TIMEOUT = httpx2.Timeout(15.0, connect=5.0)


def client() -> httpx2.Client:
    return httpx2.Client(timeout=TIMEOUT)
