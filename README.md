# SmartCart

A quick-commerce grocery app in the style of Blinkit and Zepto, with a Python backend and a React frontend.

There are three ways to shop:

| Mode | What it does |
| --- | --- |
| 🛵 **Delivery** | The classic quick-commerce flow. The nearest store that delivers to you is picked automatically, the ETA is shown ("Delivery in 8 minutes"), and the bill includes delivery, handling and small-cart fees, with a free-delivery threshold. |
| 🏬 **Scheduled pickup** | Choose a store and a 30-minute pickup slot (today or tomorrow, with limited capacity per slot). There's no delivery fee. You get a 4-digit **pickup code**, and store staff check it at the counter. |
| 🛒 **Shop in store** | You're in the store. Type or **speak** your list ("2 milk, brown bread and a dozen eggs"). The app finds each item, shows where it is (**Aisle 4 · Row 2**) and the **running total**. It sorts the list in walking order and marks the stops on a store map. At checkout you either get a **bill code** for the cashier or pay in the app (scan & go). |

Other features:

- Phone + OTP login (in dev mode the OTP is shown on screen)
- Category pages, product pages, and search that handles typos and Hindi names (`dahi`, `aloo`, `atta`)
- Cart with a live bill from the server, and a stock check before checkout
- Order tracking with a status timeline that refreshes itself
- Cancelling an order puts the items back in stock
- A **store staff dashboard** at `/staff`: verify pickup/bill codes, see a picking list with the aisle and row of every item, and move orders to their next step
- Works on phones: floating cart bar, sticky bottom total bar in in-store mode

## Tech stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2, JWT auth. Uses SQLite by default; set `SMARTCART_DATABASE_URL` to use Postgres.
- **Frontend:** React 19, TypeScript, Vite, React Router. Plain CSS, no UI framework.
- **Tests:** pytest (`backend/tests`).

## Quick start

You need Python 3.11+ and Node 20+.

**1. Backend** (http://localhost:8000; API docs at http://localhost:8000/docs)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On first start it creates `smartcart.db` and loads demo data: 3 Bengaluru stores, 11 categories, about 75 products, and stock and shelf locations for each store. To start over, run `python -m app.seed --reset`.

**2. Frontend** (http://localhost:5173), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server forwards `/api` to the backend.

### Demo logins

| Who | Phone | Notes |
| --- | --- | --- |
| Customer | any valid 10-digit number, e.g. `9876543210` | A new account is created on first login |
| Store staff | `9999999999` | Opens the dashboard at `/staff` |

In dev mode the OTP appears in the login box (click **Fill**) and in the server log.

### Try the in-store mode

1. Click **Shop in store** in the header.
2. Type `2 milk, brown bread and a dozen eggs, 1kg onion, coke`, or tap 🎤 and say it. Voice input needs Chrome, Edge or Safari.
3. Each item appears with its aisle and row, grouped in walking order, with numbered stops on the map. Tap a number to tick the item off. If a match is wrong or sold out, use **Swap**.
4. Click **Done shopping – checkout** and choose **Pay at the counter** to get a bill code. As staff, enter that code at `/staff` and mark the order completed.

## Running tests

```bash
cd backend && pytest          # 38 tests: auth, catalog/search, in-store matching, pricing, order flows
cd frontend && npm run build  # type-checks and builds
```

## Production-style run (one server)

Build the frontend and FastAPI serves it with the API from the same address:

```bash
cd frontend && npm run build
cd ../backend && SMARTCART_DEV_MODE=false SMARTCART_JWT_SECRET=$(openssl rand -hex 32) \
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

Settings are environment variables, or a `.env` file in `backend/` (see `app/config.py`):

| Variable | Default | |
| --- | --- | --- |
| `SMARTCART_DATABASE_URL` | `sqlite:///./smartcart.db` | e.g. `postgresql+psycopg://user:pass@host/db` (also install `psycopg[binary]`) |
| `SMARTCART_DEV_MODE` | `true` | Returns the OTP in the API response. **Turn this off in production.** |
| `SMARTCART_JWT_SECRET` | dev placeholder | The server refuses to start without one when dev mode is off |
| `SMARTCART_CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated |
| `SMARTCART_SEED_ON_STARTUP` | `true` | Loads demo data when the database is empty |

## Project layout

```
backend/
  app/
    main.py            FastAPI app, CORS, serves the built frontend
    models.py          Users, stores, aisles, products, per-store inventory + location, orders
    schemas.py         Request/response models
    routers/           auth, catalog, stores (pickup slots, in-store), cart, addresses, orders, staff
    services/
      search.py        Product ranking + shopping-list parser ("two packets of chips" -> 2 × chips)
      orders.py        Order creation, status flows, stock handling
      pricing.py       Bill rules (fees and thresholds in one place)
      slots.py         Pickup slot generation and capacity
      geo.py           Distance, ETA, store hours
    seed.py            Demo data
  tests/
frontend/
  src/
    context/           Auth, shop mode/store/location, cart (delivery cart + separate in-store list)
    pages/             Home, Category, Search, Product, Checkout, Orders, OrderDetail, InStore, Staff, Account
    components/        Header, ProductCard, CartDrawer, StoreMap, LoginModal, ...
    lib/api.ts         Typed API client
```

### How it's modelled

- **Money** is stored as whole numbers of **paise** (`price_paise`, `total_paise`) so rounding can't creep in. `rupees()` in `frontend/src/lib/format.ts` formats it.
- **Location** is per store: the `inventory` table holds the stock, the `aisle` and the `row_number` for every product in every store. The same product can be in Aisle 2 in one store and Aisle 5 in another.
- **Order status flows** are defined in `services/orders.py`:
  - delivery: placed → packed → out for delivery → delivered
  - pickup: placed → packed → ready for pickup → picked up
  - in-store: pay at counter → completed
- **The cart lives on the client.** The server re-prices it on every change (`POST /api/cart/quote`) and checks stock again when the order is placed.

## Roadmap ideas

- Real SMS OTP (MSG91 / Twilio) and a real payment gateway (Razorpay); payments are simulated today
- Alembic migrations, Postgres in production
- Live order updates over WebSockets instead of polling, plus a rider app with live location
- Product photos and an admin panel for catalogue, prices, stock and store layouts
- QR codes for pickup and bill codes, and barcode scanning for scan & go
- Coupons, wallet, referrals, product recommendations
