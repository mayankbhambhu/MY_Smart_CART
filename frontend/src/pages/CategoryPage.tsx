import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import ProductCard from "../components/ProductCard";
import { EmptyState, Spinner } from "../components/Loader";
import { api } from "../lib/api";
import type { Category, Product } from "../lib/types";

export default function CategoryPage() {
  const { slug } = useParams();
  const { store } = useShop();
  const { remember } = useCart();
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[] | null>(null);
  const current = categories.find((c) => c.slug === slug);

  useEffect(() => {
    api.categories().then(setCategories);
  }, []);

  useEffect(() => {
    if (!store || !current) return;
    setProducts(null);
    api.products({ storeId: store.id, categoryId: current.id, limit: 200 }).then((list) => {
      setProducts(list);
      remember(list);
    });
  }, [store?.id, current?.id, remember]);

  if (categories.length > 0 && !current) {
    return <EmptyState emoji="🤷" title="Category not found" />;
  }

  return (
    <div className="page category-page">
      <aside className="category-side" aria-label="Categories">
        {categories.map((c) => (
          <Link key={c.id} to={`/c/${c.slug}`} className={c.slug === slug ? "active" : ""}>
            <span className="category-side-emoji" style={{ background: c.color }}>
              {c.emoji}
            </span>
            <span>{c.name}</span>
          </Link>
        ))}
      </aside>
      <section className="grow">
        <h1 className="page-title">{current?.name ?? "…"}</h1>
        {products === null ? (
          <Spinner />
        ) : (
          <div className="product-grid">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
