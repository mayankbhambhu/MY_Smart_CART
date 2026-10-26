import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import { useQuote } from "../hooks/useQuote";
import { rupees } from "../lib/format";
import AddButton from "./AddButton";
import BillDetails from "./BillDetails";
import { EmptyState } from "./Loader";
import Modal from "./Modal";

export default function CartDrawer() {
  const cart = useCart();
  const { mode, store, deliveryStore } = useShop();
  const { user, requireLogin } = useAuth();
  const navigate = useNavigate();
  const { quote, error } = useQuote(store?.id, mode, cart.items, cart.drawerOpen);

  const proceed = () =>
    requireLogin(() => {
      cart.closeDrawer();
      navigate("/checkout");
    });

  const blocked = mode === "delivery" && !deliveryStore;

  return (
    <Modal title="My Cart" onClose={cart.closeDrawer} variant="drawer">
      {cart.items.length === 0 ? (
        <EmptyState emoji="🛒" title="You don't have any items in your cart">
          <p className="muted">Your favourite items are just a click away</p>
          <button className="btn btn-primary" onClick={cart.closeDrawer}>
            Start shopping
          </button>
        </EmptyState>
      ) : (
        <>
          <div className="drawer-body">
            <div className="card shipment">
              {mode === "delivery" ? (
                <>
                  <div className="shipment-title">
                    ⏱ {deliveryStore ? `Delivery in ${deliveryStore.delivery_eta_minutes} minutes` : "Not serviceable"}
                  </div>
                  <div className="muted small">
                    Shipment of {cart.count} item{cart.count > 1 ? "s" : ""} from {store?.name}
                  </div>
                </>
              ) : (
                <>
                  <div className="shipment-title">🏬 Pickup from {store?.name}</div>
                  <div className="muted small">Choose a pickup slot at checkout · no delivery fee</div>
                </>
              )}
              {cart.items.map(({ product_id, quantity }) => {
                const line = quote?.lines.find((l) => l.product.id === product_id);
                const product = line?.product ?? cart.product(product_id);
                if (!product) return null;
                return (
                  <div className="cart-line" key={product_id}>
                    <div className="cart-line-img">{product.emoji}</div>
                    <div className="grow">
                      <div className="cart-line-name">{product.name}</div>
                      <div className="muted small">{product.unit}</div>
                      <div className="price small">
                        <strong>{rupees(product.price_paise * quantity)}</strong>
                        {product.mrp_paise > product.price_paise && <s>{rupees(product.mrp_paise * quantity)}</s>}
                      </div>
                    </div>
                    <AddButton product={product} />
                  </div>
                );
              })}
            </div>
            {quote?.bill.amount_to_free_delivery_paise ? (
              <div className="nudge">
                Add items worth <strong>{rupees(quote.bill.amount_to_free_delivery_paise)}</strong> more for FREE
                delivery
              </div>
            ) : null}
            {quote && <BillDetails bill={quote.bill} showDeliveryRows={mode === "delivery"} />}
            {quote?.issues.map((issue) => (
              <p key={issue} className="error-text">
                ⚠️ {issue}
              </p>
            ))}
            {error && <p className="error-text">{error}</p>}
            {blocked && (
              <p className="error-text">We don't deliver to your location yet. Switch to Pickup to order.</p>
            )}
            <div className="card policy small muted">
              <strong>Cancellation policy</strong>
              <br />
              Orders can be cancelled until they are packed. Refunds for online payments are instant.
            </div>
          </div>
          <div className="drawer-foot">
            <button className="checkout-btn" disabled={!quote?.can_checkout || blocked} onClick={proceed}>
              <span>
                <strong>{rupees(quote?.bill.total_paise ?? cart.estimate)}</strong>
                <small>TOTAL</small>
              </span>
              <span>{user ? "Proceed" : "Login to Proceed"} ›</span>
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
