"""Policy pages: terms, privacy, refunds, shipping, contact and pricing.

Razorpay checks for these before it enables live payments, and India's Consumer Protection
(E-Commerce) Rules 2020 expect the seller's details and a grievance officer to be published. They
are plain server-rendered HTML (no JavaScript needed), filled in from the BUSINESS_* / SUPPORT_*
settings and the bill rules, so they always match what the app actually charges.

They are starting points written for this app: read them, adjust them to how you really run the
shop, and have them checked if you're unsure."""

from decimal import Decimal
from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.core.config import Settings, get_settings

LAST_UPDATED = "26 October 2026"

PAGES = {
    "/terms": "Terms & Conditions",
    "/privacy": "Privacy Policy",
    "/refund-policy": "Cancellation & Refund Policy",
    "/shipping-policy": "Shipping & Delivery Policy",
    "/pricing": "Pricing & Fees",
    "/contact": "Contact Us",
}


def _rupees(amount: Decimal | int) -> str:
    amount = Decimal(amount)
    return f"₹{amount:,.0f}" if amount == amount.to_integral() else f"₹{amount:,.2f}"


class _Business:
    """The shop's details, HTML-escaped, with visible placeholders for anything not set yet."""

    def __init__(self, settings: Settings):
        def value(field: str) -> str:
            raw = getattr(settings, field)
            return escape(raw) if raw else f"<mark>[set {field.upper()}]</mark>"

        self.brand = escape(settings.app_name)
        self.legal_name = value("business_legal_name")
        self.address = value("business_address")
        self.email = value("support_email")
        self.phone = value("support_phone")
        self.grievance_officer = value("grievance_officer")
        self.gstin = escape(settings.gstin) if settings.gstin else None
        self.email_link = (
            f'<a href="mailto:{escape(settings.support_email)}">{self.email}</a>'
            if settings.support_email
            else self.email
        )
        self.phone_link = (
            f'<a href="tel:{escape(settings.support_phone.replace(" ", ""))}">{self.phone}</a>'
            if settings.support_phone
            else self.phone
        )
        self.missing = any(
            not getattr(settings, field)
            for field in (
                "business_legal_name",
                "business_address",
                "support_email",
                "support_phone",
                "grievance_officer",
            )
        )


def _fees(settings: Settings) -> dict[str, str]:
    return {
        "free_above": _rupees(settings.free_delivery_threshold),
        "delivery": _rupees(settings.delivery_fee),
        "small_below": _rupees(settings.small_cart_threshold),
        "small": _rupees(settings.small_cart_fee),
        "handling": _rupees(settings.handling_fee),
        "hold": str(settings.payment_timeout_minutes),
    }


def _grievance(b: _Business) -> str:
    return f"""
<h2>Grievance officer</h2>
<p>If you have a complaint about an order, a payment or how we handle your data, contact our grievance
officer: <strong>{b.grievance_officer}</strong>, {b.legal_name}, {b.address}. Email {b.email_link}, phone
{b.phone_link}. We acknowledge complaints within 48 hours and aim to resolve them within one month.</p>"""


def _terms(b: _Business, f: dict[str, str]) -> str:
    return f"""
<p>{b.brand} is operated by <strong>{b.legal_name}</strong> ("we", "us"), {b.address}. By using our website or
app you agree to these terms.</p>
<h2>Your account</h2>
<p>You log in with your mobile number and a one-time code sent by SMS. Keep your phone secure: anyone with
the code can use your account. Give us accurate names, phone numbers and addresses so we can fulfil your
orders. You must be 18 or older, or use the service with a parent or guardian.</p>
<h2>Orders and prices</h2>
<p>All prices are in Indian Rupees and include applicable taxes. Your bill, with every fee, is shown before
you place an order (see <a href="/pricing">Pricing &amp; Fees</a>). An order is confirmed when it is placed
or, for online payment, when the payment succeeds. Items are subject to availability. We may cancel an
order if an item is out of stock, the address is outside our delivery area, the price shown was clearly
wrong, or we suspect fraud; any amount you paid is refunded in full.</p>
<h2>Payments</h2>
<p>You can pay online (UPI, cards, netbanking and wallets, processed securely by Razorpay), in cash or UPI
on delivery, or at the store. We never see or store your card or UPI details. An online order is held for
{f["hold"]} minutes while you pay; if the payment doesn't complete in that time the order is cancelled.</p>
<h2>Delivery, pickup and in-store shopping</h2>
<p>See our <a href="/shipping-policy">Shipping &amp; Delivery Policy</a>. Pickup orders are handed over only
against the PIN shown in your app. In-store bills are paid at the counter or in the app before you leave.</p>
<h2>Cancellations and refunds</h2>
<p>See our <a href="/refund-policy">Cancellation &amp; Refund Policy</a>.</p>
<h2>Acceptable use</h2>
<p>Don't misuse the service: no fake orders, no automated access, no attempts to break or overload it, and
no buying for resale without our agreement. We may suspend accounts that do.</p>
<h2>Liability</h2>
<p>We take care to describe products accurately, but packaging and images may differ slightly from what is
delivered. To the extent the law allows, our liability for any order is limited to the amount you paid for
it. Nothing in these terms limits your rights under the Consumer Protection Act, 2019.</p>
<h2>Changes and governing law</h2>
<p>We may update these terms; the date above shows the latest version. These terms are governed by the
laws of India, and the courts at the place of our registered address above have jurisdiction.</p>
{_grievance(b)}"""


def _privacy(b: _Business, f: dict[str, str]) -> str:
    return f"""
<p>This policy explains what personal data {b.legal_name} collects through {b.brand} and how we use it, in
line with India's Digital Personal Data Protection Act, 2023 and the IT Act, 2000.</p>
<h2>What we collect</h2>
<ul>
<li>Your mobile number (to log you in) and, if you give them, your name and email address.</li>
<li>Delivery addresses and the location you choose, to check delivery and show nearby stores.</li>
<li>Your orders, shopping lists and payment status. Card and UPI details are handled by Razorpay; we only
receive a payment reference.</li>
<li>Technical data such as your IP address and browser, used for security and to stop abuse.</li>
</ul>
<h2>How we use it</h2>
<p>To log you in, take and fulfil your orders, process payments and refunds, help you when you contact us,
prevent fraud, and meet our legal and tax obligations. We don't sell your data or use it for third-party
advertising.</p>
<h2>Who we share it with</h2>
<p>Only what each needs: our store and delivery staff (your name, phone number and address for your
order), Razorpay (payments), our SMS provider (your number, to send login codes) and our hosting provider.
We also share data when the law requires it.</p>
<h2>Storage and security</h2>
<p>Your data is stored on our hosting provider's servers and sent over encrypted connections (HTTPS).
Login codes are stored only in scrambled form and deleted within a day. We keep order records as long as
the law requires (for example for tax purposes) and other data while your account is active.</p>
<h2>Your choices and rights</h2>
<p>You can see and update your profile and addresses in the app. To get a copy of your data, correct it,
or delete your account, email {b.email_link}. We use your browser's storage only to keep you logged in and
remember your cart and lists; there are no advertising cookies.</p>
{_grievance(b)}"""


def _refunds(b: _Business, f: dict[str, str]) -> str:
    return f"""
<h2>Cancelling an order</h2>
<ul>
<li><strong>Delivery orders</strong> can be cancelled from the order page until we start packing them.</li>
<li><strong>Pickup orders</strong> can be cancelled until they are marked ready for pickup.</li>
<li><strong>In-store bills</strong> can be cancelled before they are paid.</li>
<li>An online order that isn't paid within {f["hold"]} minutes is cancelled automatically, and nothing is
charged.</li>
</ul>
<p>We may also cancel an order if items are unavailable or the address can't be served; you are told on the
order page and refunded in full.</p>
<h2>Refunds for cancelled orders</h2>
<p>If you paid online, the refund is started automatically the moment the order is cancelled, for the full
amount, to the original payment method. Banks usually show it within <strong>5–7 working days</strong>.
If a payment reaches us after an order was cancelled, or you were charged twice, the extra payment is also
refunded automatically within the same time.</p>
<h2>Damaged, wrong, missing or expired items</h2>
<p>Check your items at delivery or pickup. If something is damaged, wrong, missing or past its expiry date,
tell us within <strong>48 hours</strong> at {b.email_link} or {b.phone_link} with your order code and a photo.
We will replace the item or refund it within <strong>7 working days</strong> of confirming the problem: to
your original payment method for online payments, or by UPI or bank transfer for cash and pay-at-store
orders.</p>
<h2>What we can't take back</h2>
<p>Fresh, perishable and opened food items can't be returned unless they were damaged, wrong or expired
when you received them.</p>
<h2>Questions</h2>
<p>If a refund hasn't reached you after 7 working days, contact us at {b.email_link} with your order code.</p>
{_grievance(b)}"""


def _shipping(b: _Business, f: dict[str, str]) -> str:
    return f"""
<h2>Where we deliver</h2>
<p>We deliver within a set distance of each of our stores. When you enter your location the app tells you
whether we deliver there and from which store. We deliver within India only.</p>
<h2>How fast</h2>
<p>The estimated delivery time is shown before you order and on the order page, usually within minutes of
the order being confirmed. Weather, traffic or very high demand can delay it; the order page always shows
the latest status. If we can't deliver, we cancel the order and refund any amount paid in full.</p>
<h2>Delivery charges</h2>
<p>Delivery is free on orders of {f["free_above"]} or more; below that it costs {f["delivery"]}. Orders below
{f["small_below"]} also have a small-cart charge of {f["small"]}, and every delivery or pickup order has a
handling charge of {f["handling"]}. Every charge is shown in your bill before you pay (see
<a href="/pricing">Pricing &amp; Fees</a>).</p>
<h2>Scheduled pickup</h2>
<p>Choose a store and a pickup slot when you order; there is no delivery charge. Bring the PIN or QR code
shown in your app. If you can't make your slot, contact the store; orders not collected within 24 hours
of the slot may be cancelled, and prepaid amounts are refunded as described in our
<a href="/refund-policy">refund policy</a>.</p>
<h2>Shopping in store</h2>
<p>When you shop in the store with the app, you take your items with you after paying, so nothing is
shipped.</p>"""


def _pricing(b: _Business, f: dict[str, str]) -> str:
    return f"""
<p>All prices are in Indian Rupees (₹) and include applicable taxes (GST). Each product's price is shown on
its page and in your cart, next to the MRP when it is lower than the MRP.</p>
<h2>Charges on top of item prices</h2>
<table>
<tr>
<th>Charge</th>
<th>Delivery</th>
<th>Pickup</th>
<th>In store</th>
</tr>
<tr>
<td>Delivery charge</td>
<td>{f["delivery"]} below {f["free_above"]}, free from {f["free_above"]}</td>
<td>Free</td>
<td>None</td>
</tr>
<tr>
<td>Small-cart charge</td>
<td>{f["small"]} below {f["small_below"]}</td>
<td>None</td>
<td>None</td>
</tr>
<tr>
<td>Handling charge</td>
<td>{f["handling"]} per order</td>
<td>{f["handling"]} per order</td>
<td>None</td>
</tr>
</table>
<p>Your full bill, with every charge, is shown before you place an order or pay. There are no other fees
and no extra charge for paying online.</p>"""


def _contact(b: _Business, f: dict[str, str]) -> str:
    gstin = f"<li>GSTIN: {b.gstin}</li>" if b.gstin else ""
    return f"""
<p>We're happy to help with orders, payments, refunds or anything else.</p>
<ul>
<li>Business: <strong>{b.legal_name}</strong> (trading as {b.brand})</li>
<li>Address: {b.address}</li>
<li>Email: {b.email_link}</li>
<li>Phone: {b.phone_link}</li>
{gstin}
</ul>
<p>We reply to emails within one working day. For an order, please include its order code (for example
SC7K3M9Q), shown on the order page.</p>
{_grievance(b)}"""


_BODIES = {
    "/terms": _terms,
    "/privacy": _privacy,
    "/refund-policy": _refunds,
    "/shipping-policy": _shipping,
    "/pricing": _pricing,
    "/contact": _contact,
}

_STYLE = """
body{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  color:#1d1f1e;background:#f4f6f5}
header{background:#fff;border-bottom:1px solid #e5e7eb}
.wrap{max-width:760px;margin:0 auto;padding:16px}
header a.brand{font-weight:900;font-size:22px;text-decoration:none;color:#0a6c1a}
nav{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:6px;font-size:14px}
nav a{color:#4b5563}nav a[aria-current]{color:#0a6c1a;font-weight:700}
main{background:#fff;border-radius:16px;
  margin:16px;padding:8px 20px 20px;box-shadow:0 1px 2px rgba(0,0,0,.05)}
@media(min-width:792px){main{margin:16px auto;max-width:720px}}
h1{font-size:28px;margin:16px 0 0}h2{font-size:18px;margin:24px 0 4px}
.updated{color:#6b7280;font-size:14px;margin-top:0}
a{color:#0a6c1a}mark{background:#fef3c7;padding:0 4px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border:1px solid #e5e7eb;padding:8px;text-align:left}
th{background:#f9fafb}
.notice{background:#fef3c7;border:1px solid #fcd34d;border-radius:12px;padding:12px}
footer{color:#6b7280;font-size:13px;text-align:center;padding:8px 16px 32px}
"""


def render_policy(path: str, settings: Settings) -> str:
    business = _Business(settings)
    title = PAGES[path]
    body = _BODIES[path](business, _fees(settings))
    links = "".join(
        f'<a href="{href}"{" aria-current=page" if href == path else ""}>{escape(name)}</a>'
        for href, name in PAGES.items()
    )
    notice = (
        '<p class="notice">Before going live, set the highlighted business details in the server '
        "settings (see the README).</p>"
        if business.missing
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · {business.brand}</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{_STYLE}</style>
</head>
<body>
<header><div class="wrap"><a class="brand" href="/">{business.brand}</a><nav>{links}</nav></div></header>
<main>
<h1>{escape(title)}</h1>
<p class="updated">Last updated: {LAST_UPDATED}</p>
{notice}
{body}
</main>
<footer>© {business.legal_name} · {business.address}</footer>
</body>
</html>"""


def mount_policy_pages(app: FastAPI) -> None:
    for path in PAGES:

        def page(path: str = path) -> HTMLResponse:
            return HTMLResponse(render_policy(path, get_settings()))

        app.add_api_route(path, page, methods=["GET", "HEAD"], include_in_schema=False)
