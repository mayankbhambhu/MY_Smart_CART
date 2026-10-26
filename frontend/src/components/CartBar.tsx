import { useLocation, useNavigate } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { rupees } from "../lib/format";

/** Floating "View cart" bar shown on small screens, like the quick-commerce apps. */
export default function CartBar() {
  const cart = useCart();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  if (cart.count === 0 || ["/checkout", "/in-store"].includes(pathname) || pathname.startsWith("/staff")) return null;

  return (
    <button
      className="cart-bar"
      onClick={() => (cart.isInStoreList ? navigate("/in-store") : cart.openDrawer())}
    >
      <span>
        <span aria-hidden>{cart.isInStoreList ? "📝" : "🛒"}</span> {cart.count} item{cart.count > 1 ? "s" : ""} ·{" "}
        {rupees(cart.estimate)}
      </span>
      <strong>{cart.isInStoreList ? "View aisle route" : "View cart"} ›</strong>
    </button>
  );
}
