import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import AddButton from "../components/AddButton";
import ProductCard from "../components/ProductCard";
import { EmptyState, Spinner } from "../components/Loader";
import { api } from "../lib/api";
import { rupees } from "../lib/format";
import type { Category, Product } from "../lib/types";

export default function ProductPage() {
  const { id } = useParams();
  const { store, mode } = useShop();
  const { remember } = useCart();
  const [product, setProduct] = useState<Product | null>(null);
  const [similar, setSimilar] = useState<Product[]>([]);
  const [category, setCategory] = useState<Category | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    if (!store || !id) return;
    setMissing(false);
    api
      .product(Number(id), store.id)
      .then(async (p) => {
        setProduct(p);
        remember([p]);
        const [cats, list] = await Promise.all([
          api.categories(),
          api.products({ storeId: store.id, categoryId: p.category_id, limit: 12 }),
        ]);
        setCategory(cats.find((c) => c.id === p.category_id) ?? null);
        setSimilar(list.filter((x) => x.id !== p.id));
      })
      .catch(() => setMissing(true));
  }, [id, store?.id, remember]);

  if (missing) return <EmptyState emoji="🤷" title="Product not found" />;
  if (!product) return <Spinner />;

  return (
    <div className="page">
      <nav className="crumbs small muted">
        <Link to="/">Home</Link> / {category && <Link to={`/c/${category.slug}`}>{category.name}</Link>} /{" "}
        {product.name}
      </nav>
      <div className="product-detail">
        <div className="product-detail-img">{product.emoji}</div>
        <div className="product-detail-info">
          {product.brand && <div className="muted">{product.brand}</div>}
          <h1>{product.name}</h1>
          <div className="muted">{product.unit}</div>
          <div className="price big">
            <strong>{rupees(product.price_paise)}</strong>
            {product.mrp_paise > product.price_paise && (
              <>
                <s>MRP {rupees(product.mrp_paise)}</s>
                <span className="discount-inline">{product.discount_percent}% OFF</span>
              </>
            )}
          </div>
          <div className="muted small">(Inclusive of all taxes)</div>
          <div style={{ margin: "16px 0" }}>
            <AddButton product={product} size="lg" />
          </div>
          {product.location && store && (
            <div className={`card location-card${mode === "in_store" ? " highlight" : ""}`}>
              📍 At <strong>{store.name}</strong> you'll find this in <strong>{product.location.label}</strong>
              <div className="muted small">{product.location.aisle_name}</div>
            </div>
          )}
          <div className="card">
            <h3>Why shop from SmartCart?</h3>
            <ul className="why">
              <li>⚡ Superfast delivery to your doorstep from dark stores near you</li>
              <li>🏬 Or schedule a free pickup and collect from the store</li>
              <li>📍 In the store? We'll tell you the exact aisle and row</li>
            </ul>
          </div>
          {product.description && <p className="muted">{product.description}</p>}
        </div>
      </div>
      {similar.length > 0 && (
        <section className="rail">
          <div className="rail-head">
            <h2>Similar products</h2>
          </div>
          <div className="rail-scroll">
            {similar.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
