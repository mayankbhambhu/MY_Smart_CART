import type { MouseEvent } from "react";
import { useCart } from "../context/CartContext";
import type { Product } from "../lib/types";

export default function AddButton({ product, size = "md" }: { product: Product; size?: "md" | "lg" }) {
  const cart = useCart();
  const qty = cart.quantity(product.id);

  if (!product.in_stock && qty === 0) {
    return <span className={`add-btn add-btn-${size} disabled`}>Sold out</span>;
  }
  if (qty === 0) {
    return (
      <button
        className={`add-btn add-btn-${size}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          cart.add(product);
        }}
      >
        ADD
      </button>
    );
  }
  const limit = product.stock ?? Infinity;
  // The card around this button is a link, so keep clicks from navigating.
  const change = (e: MouseEvent, next: number) => {
    e.preventDefault();
    e.stopPropagation();
    cart.setQuantity(product.id, next);
  };
  return (
    <div className={`stepper stepper-${size}`} onClick={(e) => e.preventDefault()}>
      <button aria-label="Remove one" onClick={(e) => change(e, qty - 1)}>
        −
      </button>
      <span>{qty}</span>
      <button aria-label="Add one" disabled={qty >= limit} onClick={(e) => change(e, qty + 1)}>
        +
      </button>
    </div>
  );
}
