import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import ProductCard from "../components/ProductCard";
import { EmptyState, Spinner } from "../components/Loader";
import { api } from "../lib/api";
import type { Product } from "../lib/types";

const TRENDING = ["milk", "bread", "eggs", "atta", "chips", "coke", "curd", "onion"];

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const { store } = useShop();
  const { remember } = useCart();
  const [results, setResults] = useState<Product[] | null>(null);

  useEffect(() => {
    if (!store || !q) {
      setResults(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      api.products({ storeId: store.id, q }).then((list) => {
        if (cancelled) return;
        setResults(list);
        remember(list);
      });
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [q, store?.id, remember]);

  if (!q) {
    return (
      <div className="page">
        <h2 className="section-title">Trending searches</h2>
        <div className="chips">
          {TRENDING.map((t) => (
            <button key={t} className="chip" onClick={() => setParams({ q: t })}>
              🔍 {t}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1 className="page-title">Showing results for "{q}"</h1>
      {results === null ? (
        <Spinner />
      ) : results.length === 0 ? (
        <EmptyState emoji="🔎" title={`No results for "${q}"`}>
          <p className="muted">Try a different spelling or a more general word.</p>
        </EmptyState>
      ) : (
        <div className="product-grid">
          {results.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  );
}
