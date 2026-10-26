import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import ProductCard from "../components/ProductCard";
import { Spinner } from "../components/Loader";
import { api } from "../lib/api";
import type { Category, CategoryWithProducts } from "../lib/types";

export default function Home() {
  const { store, mode, setMode, deliveryStore, loading } = useShop();
  const { remember } = useCart();
  const navigate = useNavigate();
  const [rails, setRails] = useState<CategoryWithProducts[] | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!store) return;
    setRails(null);
    api
      .home(store.id)
      .then((data) => {
        setRails(data);
        remember(data.flatMap((r) => r.products));
      })
      .catch((err) => setError(err.message));
  }, [store?.id, remember]);

  if (loading && !store) return <Spinner label="Finding the nearest store…" />;
  if (!store) return <div className="page">{error ?? "No stores available. Is the backend running?"}</div>;

  return (
    <div className="page">
      {mode === "delivery" && !deliveryStore && (
        <div className="banner warn">
          😔 We don't deliver to this location yet. You can still{" "}
          <button className="link-btn" onClick={() => setMode("pickup")}>
            schedule a pickup
          </button>{" "}
          from {store.name}.
        </div>
      )}

      <section className="hero-grid">
        <div className="hero hero-main">
          <div>
            <h1>Stock up on daily essentials</h1>
            <p>Get farm-fresh goodness &amp; a range of exotic fruits, vegetables, eggs &amp; more</p>
            <button className="btn btn-dark" onClick={() => navigate("/c/fruits-vegetables")}>
              Shop now
            </button>
          </div>
          <span className="hero-emoji" aria-hidden>
            🥬🍅🥚
          </span>
        </div>
        <button className="hero hero-pickup" onClick={() => setMode("pickup")}>
          <h2>Skip the delivery fee</h2>
          <p>Schedule a pickup slot and collect your order from the store</p>
          <span className="pill">🏬 Schedule pickup ›</span>
        </button>
        <button
          className="hero hero-instore"
          onClick={() => {
            setMode("in_store");
            navigate("/in-store");
          }}
        >
          <h2>Shopping in the store?</h2>
          <p>Tell us your list and we'll show the aisle &amp; row for every item, plus your total</p>
          <span className="pill">📍 Find my items ›</span>
        </button>
      </section>

      <section className="category-grid" aria-label="Categories">
        {categories.map((c) => (
          <Link key={c.id} to={`/c/${c.slug}`} className="category-tile">
            <span className="category-emoji" style={{ background: c.color }}>
              {c.emoji}
            </span>
            <span>{c.name}</span>
          </Link>
        ))}
      </section>

      {rails === null ? (
        <Spinner />
      ) : (
        rails.map((rail) => (
          <section key={rail.id} className="rail">
            <div className="rail-head">
              <h2>{rail.name}</h2>
              <Link to={`/c/${rail.slug}`}>see all</Link>
            </div>
            <div className="rail-scroll">
              {rail.products.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
