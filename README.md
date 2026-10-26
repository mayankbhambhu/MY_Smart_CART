# Smart Cart 🛒

A quick-commerce app in the style of Blinkit / Zepto, with a **Python (FastAPI) backend** and a **React web app**, plus two new ways to shop:

- **Scheduled pickup**: order in the app, choose a time slot, and collect from the store with no delivery fee.
- **In-store shopping**: tell the app what you want (type it or say it). It shows where each item is, like **Aisle 4 · Row 2**, gives you the best walking route and keeps a running **total**. Pay at the counter with a QR bill, or in the app.

**Live demo:** <https://smart-cart-imbj.onrender.com>. It runs on Render's free plan, so the first visit after a quiet spell can take about a minute. Login codes show on screen and payments are simulated.

![Home, scheduled pickup, in-store aisle list and store map](docs/app-screens.png)

## Features

**Shopping (mobile-first web app, also works on desktop)**
- Phone number + OTP login with codes sent by SMS (MSG91 or Twilio). On demo deployments the code is shown on screen instead.
- A **Delivery / Pickup / In-store** switch in the header changes the whole app
- "Delivery in 8 minutes" based on your location, serviceability check, saved addresses
- Home banners, category grid, product rails, category pages with a sidebar, product pages
- Search that copes with typos, partial words and Hindi names (`doodh`, `pyaz`, `cheeni`, `atta`)
- Cart and checkout with a bill worked out on the server: item total, MRP savings, delivery fee (free above ₹199), handling charge and small-cart fee
- Order tracking with a live status timeline, plus cancellation while it's still allowed

**Payments (Razorpay)**
- Pay online with UPI, cards, netbanking or wallets through Razorpay Checkout. Cash on delivery and pay-at-store still work.
- While the customer pays, the order holds its stock and pickup slot for 15 minutes. Unpaid orders are then cancelled and everything is released.
- Each payment is checked three ways: the Checkout signature, a call to Razorpay's API, and a signed webhook. It's recorded exactly once even when all three arrive together. A lost callback is picked up by the webhook or the "Already paid? Check again" button.
- Cancelling a paid order refunds it through Razorpay. A payment that arrives after an order expired, or after the bill was paid at the counter, is refunded automatically.
- Without Razorpay keys, a built-in **test checkout** stands in so the whole flow can be tried. No money moves.

**Scheduled pickup**
- Pick a store and a 30-minute slot for today or the next two days. Slots follow the store's pickup hours, a 30-minute packing lead time and a per-slot capacity.
- No delivery fee. Pay at the store or online.
- The pickup pass has a QR code and a 4-digit PIN. Staff can only hand the order over with the right PIN.

**In-store shopping**
- Type or speak a list, for example `2 milk, bread, 6 eggs, 1kg atta, maggi` or `do doodh aur ek kilo cheeni`. Voice uses the browser's Web Speech API (Chrome, Edge, Safari).
- Understands quantities (`2`, `two`, `do`, `x2`), pack sizes (`1kg`, `500 ml`) and pieces (`6 eggs` means one 6-pack). It also splits lists spoken without commas (`milk bread eggs`).
- Shows each item's **aisle & row** in the chosen store, grouped by aisle in walking order. There's a store map with the route, tick-boxes for items you've picked up, brand/size swaps, and a live total with savings.
- Checkout: **pay at the counter** (the cashier scans the bill QR, with no re-scanning of items) or **pay in the app** with Razorpay.

**Store dashboard** (`/staff`)
- Pickup, delivery and in-store queues for the staff member's store, refreshed automatically
- Picking lists sorted by aisle and row
- Status updates in one tap, PIN-checked pickup handover, and bill lookup by code with a "Payment received" button

![Store staff dashboard](docs/staff-dashboard.png)

## Tech stack

| Layer | Tools |
| --- | --- |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic 2, PyJWT, RapidFuzz (fuzzy matching), SQLite locally / PostgreSQL in production |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, React Router 8, TanStack Query, Zustand, lucide icons |
| Services | Razorpay (payments), MSG91 or Twilio (SMS), Render (hosting) |
| Quality | pytest (86 tests, run on SQLite and PostgreSQL), ruff, oxlint, strict TypeScript |

## Run it locally

You need **Python 3.12+** and **Node 22+**. Use two terminals.

```bash
# Terminal 1: API on http://localhost:8000 (interactive docs at /docs)
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Terminal 2: web app on http://localhost:5173
cd frontend
npm install
npm run dev
```

On first start the backend creates `backend/smartcart.db` (SQLite) and loads demo data: 188 products in 12 categories, and 3 Gurugram stores, each with its own aisle layout. To start over, run `python -m app.seed --reset` in `backend/`.

### Demo accounts

| Who | Phone | Notes |
| --- | --- | --- |
| Customer | `9876543210` | Has a saved address in Sector 29 |
| Store staff | `9000000001` / `9000000002` / `9000000003` | Sector 29 / DLF Phase 3 / Sohna Road stores |
| Admin | `9999999999` | Sees every store's orders |

Any other valid 10-digit mobile number signs up a new customer. These accounts only exist while login codes are shown on screen (`SMS_PROVIDER=console`). With real SMS, the made-up staff and admin numbers lose their access. Use `ADMIN_PHONES` or `python -m app.manage set-role` for your own numbers.

### Things to try

1. **Delivery**: add a few items, open the cart, log in and place the order. In demo mode orders move through their statuses on their own, so you can watch tracking update. Choose **Pay online now** to try the payment flow. Without Razorpay keys a test checkout opens, where you can also simulate a failed payment.
2. **Scheduled pickup**: switch to **Pickup**, add items, choose a slot and schedule it, and note the PIN. Then open a private window, log in as `9000000001` and go to **Store dashboard**. Confirm the order, start packing, mark it ready, enter the PIN and hand it over.
3. **In-store**: tap **In-store**, type or say your list, then look at the aisle list and the **Store map**. Tick items off and check out with **Pay at the counter**. On the staff dashboard, look up the bill code and press **Payment received**.

## Deploy on Render (free)

The repository includes a [Render Blueprint](render.yaml). It sets up one web service, where FastAPI serves the API and the built React app from the same address, plus a PostgreSQL database. Every push to the branch redeploys. If you merge this work into another branch, change `branch:` in `render.yaml` to match.

1. Sign in at [render.com](https://render.com) with GitHub and allow access to this repository.
2. Choose **New → Blueprint**, pick this repository and the branch that contains `render.yaml` (`claude/quick-commerce-scheduled-pickup-7k33uo` until it's merged into your main branch), then apply. The build runs [`scripts/render-build.sh`](scripts/render-build.sh) to install Python packages and build the frontend. The first deploy takes a few minutes.
3. Open `https://<service-name>.onrender.com`. It starts in **demo mode**: login codes show on screen and payments use the test checkout. A banner at the top says so.

On the free plan the app sleeps after 15 minutes without visitors, and the next visit takes about a minute to wake it. The free database expires 30 days after it's created unless you upgrade it. Razorpay retries webhooks, so payments made while the app sleeps are still recorded.

To run the production setup yourself: `./scripts/render-build.sh`, then `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`. Set `DATABASE_URL`, `SECRET_KEY` and `ENVIRONMENT` first.

## Going live: payments and SMS

All of these are environment variables. On Render, add them in the service's **Environment** tab; the app restarts with them.

**1. Razorpay**
1. Create a [Razorpay](https://razorpay.com) account. In the Dashboard, under **Account & Settings → API Keys**, generate keys. Start in **Test Mode**.
2. Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`. "Pay online" now opens Razorpay Checkout.
3. Under **Webhooks**, add `https://<your-app>/api/payments/razorpay/webhook` with the events `payment.captured`, `order.paid` and `payment.failed`. Choose a secret and set the same value as `RAZORPAY_WEBHOOK_SECRET`.
4. Test with Razorpay's [test UPI IDs](https://razorpay.com/docs/payments/payments/test-upi-details/) (`success@razorpay`, `failure@razorpay`) or their test cards.
5. Once Razorpay activates your account (KYC), swap in the live keys (`rzp_live_...`) and add the webhook again in Live Mode.

Keep Razorpay's default automatic capture. The app captures payments itself if your account is set to manual capture.

**2. SMS login codes**
- **MSG91** (India): in India, business SMS must come from a DLT-registered sender ID using a DLT-approved template. Create an OTP template containing `##OTP##` in MSG91, then set `SMS_PROVIDER=msg91`, `MSG91_AUTH_KEY` and `MSG91_OTP_TEMPLATE_ID`.
- **Twilio**: set `SMS_PROVIDER=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` and `TWILIO_FROM` (a number or a Messaging Service SID). Indian numbers still need DLT registration.
- Optional: set `WEBOTP_DOMAIN` to your site's domain. Chrome on Android can then fill the code in from the SMS.

Codes are rate-limited per number, per network and overall per hour. That caps the bill if someone tries to pump SMS through the login form. A failed send shows an error and isn't counted.

**3. Your admin account and staff**
- Set `ADMIN_PHONES` to your mobile number, or several numbers separated by commas. After the restart, log in with an SMS code to see every store's orders.
- To make someone store staff, run this from your computer with `DATABASE_URL` pointing at the hosted database (Render shows an External Database URL):

  ```bash
  cd backend && DATABASE_URL='postgresql://...' python -m app.manage set-role 98XXXXXXXX staff --store sector-29
  ```

**4. Switch to production.** Set `ENVIRONMENT=production` and `SIMULATE_ORDER_PROGRESS=false`, so orders only move when the store team moves them. Production refuses to start without real SMS and a proper `SECRET_KEY`, and never offers the test checkout.

## Configuration

Every setting can be set as an environment variable or in `backend/.env` (see [`backend/.env.example`](backend/.env.example)).

| Variable | Default | What it does |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./smartcart.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `ENVIRONMENT` | `development` | `development`, `test`, `demo` (hosted, codes on screen allowed) or `production` |
| `SECRET_KEY` | dev value | Signs login tokens (required on any hosted deployment) |
| `SMS_PROVIDER` | `console` | `console` (code shown on screen), `msg91` or `twilio`, plus their keys (see above) |
| `OTP_MAX_PER_PHONE_PER_HOUR` / `OTP_MAX_PER_IP_PER_HOUR` / `OTP_MAX_PER_HOUR` | `5` / `30` / `300` | Login code limits |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` | not set | Razorpay payments (see above) |
| `SIMULATED_PAYMENTS` | `true` | Test checkout when there are no Razorpay keys (never in production) |
| `PAYMENT_TIMEOUT_MINUTES` | `15` | How long an unpaid online order holds its stock and slot |
| `ADMIN_PHONES` | not set | Numbers that get the admin role on startup |
| `AUTO_SEED` | `true` | Loads demo data into an empty database |
| `FREE_DELIVERY_THRESHOLD` / `DELIVERY_FEE` | `199` / `25` | Delivery charge rules (₹) |
| `SMALL_CART_THRESHOLD` / `SMALL_CART_FEE` | `99` / `20` | Small-cart charge (₹) |
| `HANDLING_FEE` | `2` | Per delivery or pickup order (₹) |
| `PICKUP_LEAD_MINUTES` | `30` | Earliest pickup slot after ordering |
| `SIMULATE_ORDER_PROGRESS` | `true` | Moves orders through their statuses automatically (demo) |
| `CORS_ORIGINS` | Vite dev server | Browser origins allowed to call the API |

## Project layout

```
backend/
  app/
    api/routes/      auth, catalog, stores, cart, addresses, orders, payments, instore, staff
    core/            settings, database, security (JWT + OTP), money/time column types
    models/          users, catalog, stores (aisles + per-store stock & location), orders, payments
    schemas/         request/response models
    services/        pricing, pickup slots, orders, payments + Razorpay client, SMS, product matching
    seed/            demo catalog, stores and accounts  (python -m app.seed --reset)
    manage.py        admin commands (python -m app.manage set-role ...)
  tests/             pytest suite (Razorpay and the SMS gateways are faked)
scripts/render-build.sh   build step used by Render
render.yaml               Render Blueprint
frontend/
  src/
    pages/           Home, Categories, Search, Product, Cart, InStore, Orders, Staff, ...
    components/      layout, product cards, store map, sheets, order widgets
    lib/             API client, queries, payments (Razorpay Checkout), formatting, voice input
    store/           cart, location/mode, in-store lists, auth (persisted in the browser)
```

## API at a glance

Full interactive docs: <http://localhost:8000/docs>

| Method & path | Purpose |
| --- | --- |
| `GET /api/config` | What this deployment supports (SMS or on-screen codes, Razorpay or test payments) |
| `POST /api/auth/otp/request`, `POST /api/auth/otp/verify` | Phone login |
| `GET /api/home`, `/api/categories/{slug}`, `/api/products/{id}`, `/api/search?q=` | Catalog. Add `store_id` to get stock and the aisle/row location. |
| `GET /api/stores`, `/api/stores/serviceability`, `/api/stores/{id}/pickup-slots` | Stores, delivery ETA, pickup slots |
| `POST /api/cart/quote` | Prices a cart for delivery, pickup or in-store |
| `POST /api/orders`, `GET /api/orders`, `POST /api/orders/{id}/cancel` | Delivery and pickup orders |
| `POST /api/instore/{store_id}/resolve` | **Shopping list → products with aisle, row, walking order and total** |
| `POST /api/instore/{store_id}/checkout` | In-store bill (pay at the counter or in the app) |
| `POST /api/payments/orders/{id}/session` | Starts paying for an order: the Razorpay order for Checkout |
| `POST /api/payments/orders/{id}/razorpay/verify`, `POST /api/payments/orders/{id}/refresh` | Confirms a payment (signature + Razorpay API) / re-checks an unpaid order |
| `POST /api/payments/razorpay/webhook` | Razorpay webhooks (signature-checked) |
| `GET /api/staff/orders`, `POST /api/staff/orders/{id}/status`, `POST /api/staff/orders/{id}/complete` | Store dashboard |

Example:

```bash
curl -s localhost:8000/api/instore/1/resolve -H 'content-type: application/json' \
  -d '{"text": "2 milk, bread, 6 eggs, 1kg atta, maggi"}'
# → items in walking order, e.g. "Amul Taaza Toned Milk · Aisle 2 · Row 1", plus total and savings
```

## How the item finder works

`backend/app/services/matching.py` splits the list on commas, "and" and "aur", then reads quantities and pack sizes. Each phrase is scored against product names, brands, subcategories and tags (synonyms and Hindi names), with tolerance for typos and half-typed words. When a phrase spoken without commas doesn't match a single product well, it finds the best way to split it into several products. Matches are looked up in that store's inventory (`store_inventory` holds each product's stock, aisle and row per store) and ordered in a snake route: up the first aisle you need, down the next, and so on.

## Tests and checks

```bash
cd backend && pytest && ruff check app tests
TEST_DATABASE_URL=postgresql://localhost/smartcart_test pytest   # the same suite on PostgreSQL
cd frontend && npm run lint && npm run build
```

## What's next

- Push or WhatsApp order updates
- Alembic migrations, so later schema changes can be applied to the hosted database
- Product photos, and an admin panel for catalog, prices, stock and aisle layouts
- Scan-and-go barcode scanning in store, a rider app, coupons and offers
- Live order updates over WebSockets instead of polling
