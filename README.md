# Smart Cart 🛒

A quick-commerce app in the style of Blinkit / Zepto, with a **Python (FastAPI) backend** and a **React web app**, plus two new ways to shop:

- **Scheduled pickup**: order in the app, choose a time slot, and collect from the store with no delivery fee.
- **In-store shopping**: tell the app what you want (type it or say it). It shows where each item is, like **Aisle 4 · Row 2**, gives you the best walking route and keeps a running **total**. Pay at the counter with a QR bill, or in the app.

![Home, scheduled pickup, in-store aisle list and store map](docs/app-screens.png)

## Features

**Shopping (mobile-first web app, also works on desktop)**
- Phone number + OTP login (in development the OTP is shown on screen)
- A **Delivery / Pickup / In-store** switch in the header changes the whole app
- "Delivery in 8 minutes" based on your location, serviceability check, saved addresses
- Home banners, category grid, product rails, category pages with a sidebar, product pages
- Search that copes with typos, partial words and Hindi names (`doodh`, `pyaz`, `cheeni`, `atta`)
- Cart and checkout with a bill worked out on the server: item total, MRP savings, delivery fee (free above ₹199), handling charge and small-cart fee
- Order tracking with a live status timeline, plus cancellation while it's still allowed

**Scheduled pickup**
- Pick a store and a 30-minute slot for today or the next two days. Slots follow the store's pickup hours, a 30-minute packing lead time and a per-slot capacity.
- No delivery fee. Pay at the store or online.
- The pickup pass has a QR code and a 4-digit PIN. Staff can only hand the order over with the right PIN.

**In-store shopping**
- Type or speak a list, for example `2 milk, bread, 6 eggs, 1kg atta, maggi` or `do doodh aur ek kilo cheeni`. Voice uses the browser's Web Speech API (Chrome, Edge, Safari).
- Understands quantities (`2`, `two`, `do`, `x2`), pack sizes (`1kg`, `500 ml`) and pieces (`6 eggs` means one 6-pack). It also splits lists spoken without commas (`milk bread eggs`).
- Shows each item's **aisle & row** in the chosen store, grouped by aisle in walking order. There's a store map with the route, tick-boxes for items you've picked up, brand/size swaps, and a live total with savings.
- Checkout: **pay at the counter** (the cashier scans the bill QR, with no re-scanning of items) or **pay in the app**.

**Store dashboard** (`/staff`)
- Pickup, delivery and in-store queues for the staff member's store, refreshed automatically
- Picking lists sorted by aisle and row
- Status updates in one tap, PIN-checked pickup handover, and bill lookup by code with a "Payment received" button

![Store staff dashboard](docs/staff-dashboard.png)

## Tech stack

| Layer | Tools |
| --- | --- |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic 2, PyJWT, RapidFuzz (fuzzy matching), SQLite (switchable to PostgreSQL) |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, React Router 8, TanStack Query, Zustand, lucide icons |
| Quality | pytest (49 tests), ruff, oxlint, strict TypeScript |

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

Any other valid 10-digit mobile number signs up a new customer. In development the OTP is shown on the login screen.

### Things to try

1. **Delivery**: add a few items, open the cart, log in and place the order. In demo mode orders move through their statuses on their own, so you can watch tracking update.
2. **Scheduled pickup**: switch to **Pickup**, add items, choose a slot and schedule it, and note the PIN. Then open a private window, log in as `9000000001` and go to **Store dashboard**. Confirm the order, start packing, mark it ready, enter the PIN and hand it over.
3. **In-store**: tap **In-store**, type or say your list, then look at the aisle list and the **Store map**. Tick items off and check out with **Pay at the counter**. On the staff dashboard, look up the bill code and press **Payment received**.

## Production: one process

```bash
cd frontend && npm run build                   # builds frontend/dist
cd ../backend
export ENVIRONMENT=production SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" OTP_DEV_MODE=false
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

FastAPI then serves both the API (`/api/...`) and the built web app from the same address. In production the server refuses to start with the default secret or with `OTP_DEV_MODE` on. Connect an SMS provider in `backend/app/services/notifications.py` first, or nobody can receive their login code.

## Configuration

Every setting can be set as an environment variable or in `backend/.env` (see [`backend/.env.example`](backend/.env.example)).

| Variable | Default | What it does |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./smartcart.db` | Any SQLAlchemy URL, e.g. PostgreSQL |
| `SECRET_KEY` | dev value | Signs login tokens (required in production) |
| `OTP_DEV_MODE` | `true` | Shows the OTP on screen instead of sending an SMS |
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
    api/routes/      auth, catalog, stores, cart, addresses, orders, instore, staff
    core/            settings, database, security (JWT + OTP), money/time column types
    models/          users, catalog, stores (aisles + per-store stock & location), orders
    schemas/         request/response models
    services/        pricing, pickup slots, orders, product matching, in-store lists
    seed/            demo catalog, stores and accounts  (python -m app.seed --reset)
  tests/             pytest suite
frontend/
  src/
    pages/           Home, Categories, Search, Product, Cart, InStore, Orders, Staff, ...
    components/      layout, product cards, store map, sheets, order widgets
    lib/             API client, queries, formatting, voice input
    store/           cart, location/mode, in-store lists, auth (persisted in the browser)
```

## API at a glance

Full interactive docs: <http://localhost:8000/docs>

| Method & path | Purpose |
| --- | --- |
| `POST /api/auth/otp/request`, `POST /api/auth/otp/verify` | Phone login |
| `GET /api/home`, `/api/categories/{slug}`, `/api/products/{id}`, `/api/search?q=` | Catalog. Add `store_id` to get stock and the aisle/row location. |
| `GET /api/stores`, `/api/stores/serviceability`, `/api/stores/{id}/pickup-slots` | Stores, delivery ETA, pickup slots |
| `POST /api/cart/quote` | Prices a cart for delivery, pickup or in-store |
| `POST /api/orders`, `GET /api/orders`, `POST /api/orders/{id}/cancel` | Delivery and pickup orders |
| `POST /api/instore/{store_id}/resolve` | **Shopping list → products with aisle, row, walking order and total** |
| `POST /api/instore/{store_id}/checkout` | In-store bill (pay at the counter or in the app) |
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
cd frontend && npm run lint && npm run build
```

## What's next

- Real payments (Razorpay / UPI intent); online payment is simulated today
- SMS provider for OTPs, plus push or WhatsApp order updates
- PostgreSQL with Alembic migrations once the schema settles
- Product photos, and an admin panel for catalog, prices, stock and aisle layouts
- Scan-and-go barcode scanning in store, a rider app, coupons and offers
- Live order updates over WebSockets instead of polling
