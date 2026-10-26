import { Link } from "react-router-dom";
import { useShop } from "../context/ShopContext";
import { rupees } from "../lib/format";
import type { Product } from "../lib/types";
import AddButton from "./AddButton";

export default function ProductCard({ product }: { product: Product }) {
  const { mode, store } = useShop();
  return (
    <Link to={`/p/${product.id}`} className={`product-card${product.in_stock ? "" : " out"}`}>
      {product.discount_percent > 0 && <span className="discount-tag">{product.discount_percent}% OFF</span>}
      <div className="product-img">
        {product.image_url ? <img src={product.image_url} alt="" /> : <span aria-hidden>{product.emoji}</span>}
      </div>
      {mode === "delivery" && store?.delivery_eta_minutes && (
        <span className="eta-chip">⏱ {store.delivery_eta_minutes} MINS</span>
      )}
      {mode === "in_store" && product.location && <span className="aisle-chip">📍 {product.location.label}</span>}
      {mode === "pickup" && <span className="eta-chip pickup">🏬 Pickup</span>}
      <div className="product-name">{product.name}</div>
      <div className="product-unit">{product.unit}</div>
      <div className="product-foot">
        <div className="price">
          <strong>{rupees(product.price_paise)}</strong>
          {product.mrp_paise > product.price_paise && <s>{rupees(product.mrp_paise)}</s>}
        </div>
        <AddButton product={product} />
      </div>
    </Link>
  );
}
