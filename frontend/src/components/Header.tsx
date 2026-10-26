import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import { rupees } from "../lib/format";
import type { Mode } from "../lib/types";
import LocationModal from "./LocationModal";
import StoreModal from "./StoreModal";

const MODES: { id: Mode; icon: string; label: string; hint: string }[] = [
  { id: "delivery", icon: "🛵", label: "Delivery", hint: "in minutes" },
  { id: "pickup", icon: "🏬", label: "Pickup", hint: "schedule a slot" },
  { id: "in_store", icon: "🛒", label: "Shop in store", hint: "find any aisle" },
];

const SEARCH_HINTS = ["milk", "bread", "atta", "chips", "eggs", "coffee", "detergent"];

export default function Header() {
  const { mode, setMode, location, store, deliveryStore, loading } = useShop();
  const { user, requireLogin } = useAuth();
  const cart = useCart();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const [picker, setPicker] = useState<"location" | "store" | null>(null);
  const [hint, setHint] = useState(0);
  const query = pathname === "/search" ? (params.get("q") ?? "") : "";

  useEffect(() => {
    const id = setInterval(() => setHint((h) => (h + 1) % SEARCH_HINTS.length), 2500);
    return () => clearInterval(id);
  }, []);

  const onSearch = (value: string) => {
    navigate(`/search?q=${encodeURIComponent(value)}`, { replace: pathname === "/search" });
  };

  const changeMode = (next: Mode) => {
    setMode(next);
    if (next === "in_store") navigate("/in-store");
    else if (pathname === "/in-store") navigate("/");
  };

  let title: string;
  let subtitle: string;
  if (mode === "delivery") {
    title = loading
      ? "Finding nearest store…"
      : deliveryStore
        ? `Delivery in ${deliveryStore.delivery_eta_minutes} minutes`
        : "Not delivering here yet";
    subtitle = location.label;
  } else {
    title = mode === "pickup" ? "Pickup from" : "Shopping at";
    subtitle = store?.name ?? "Choose a store";
  }

  return (
    <header className="header">
      <div className="header-main">
        <Link to="/" className="logo" aria-label="SmartCart home">
          smart<span>cart</span>
        </Link>
        <button className="where" onClick={() => setPicker(mode === "delivery" ? "location" : "store")}>
          <strong>{title}</strong>
          <span>
            {subtitle} <span aria-hidden>▾</span>
          </span>
        </button>
        <label className="search">
          <span aria-hidden>🔍</span>
          <input
            value={query}
            onChange={(e) => onSearch(e.target.value)}
            onFocus={() => pathname !== "/search" && onSearch("")}
            placeholder={`Search "${SEARCH_HINTS[hint]}"`}
            aria-label="Search products"
          />
        </label>
        {user ? (
          <Link to="/account" className="account-btn">
            <span aria-hidden>👤</span>
            <span className="hide-sm">{user.name || "Account"}</span>
          </Link>
        ) : (
          <button className="account-btn" onClick={() => requireLogin()}>
            <span aria-hidden>👤</span>
            <span className="hide-sm">Login</span>
          </button>
        )}
        <button
          className="cart-btn"
          onClick={() => (cart.isInStoreList ? navigate("/in-store") : cart.openDrawer())}
          aria-label="Open cart"
        >
          <span aria-hidden>{cart.isInStoreList ? "📝" : "🛒"}</span>
          {cart.count > 0 ? (
            <span className="cart-btn-text">
              <span>
                {cart.count} item{cart.count > 1 ? "s" : ""}
              </span>
              <strong>{rupees(cart.estimate)}</strong>
            </span>
          ) : (
            <span className="cart-btn-text hide-sm">{cart.isInStoreList ? "My list" : "My Cart"}</span>
          )}
        </button>
      </div>
      <nav className="mode-tabs" aria-label="How do you want to shop?">
        {MODES.map((m) => (
          <button key={m.id} className={mode === m.id ? "active" : ""} onClick={() => changeMode(m.id)}>
            <span aria-hidden>{m.icon}</span>
            <span>
              <strong>{m.label}</strong>
              <small>{m.hint}</small>
            </span>
          </button>
        ))}
      </nav>
      {picker === "location" && <LocationModal onClose={() => setPicker(null)} />}
      {picker === "store" && <StoreModal onClose={() => setPicker(null)} />}
    </header>
  );
}
