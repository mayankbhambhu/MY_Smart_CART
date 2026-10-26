# Smart Cart web app

React 19 + TypeScript + Vite + Tailwind CSS 4. See the [main README](../README.md) for the full picture.

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to the FastAPI server on :8000
npm run lint     # oxlint
npm run build    # type-check and build to dist/ (FastAPI serves it in production)
```

Set `VITE_API_PROXY` to point the dev proxy somewhere other than `http://localhost:8000`, or
`VITE_API_URL` to call an API on another origin directly.

Where things live:

- `src/pages/`: one file per screen (home, category, search, product, cart/checkout, in-store, orders, staff…)
- `src/components/`: header and navigation, product cards, store map, sheets, order widgets
- `src/lib/`: API client and query hooks, types that mirror the backend schemas, formatting, voice input
- `src/store/`: cart, shopping mode and location, in-store lists, and session (kept in localStorage)
