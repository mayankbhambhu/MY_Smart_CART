import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import BillDetails from "../components/BillDetails";
import { EmptyState, Spinner } from "../components/Loader";
import { api, ApiError } from "../lib/api";
import { dateTimeLabel, rupees, slotLabel, timeLabel } from "../lib/format";
import type { Order } from "../lib/types";

const FINAL = new Set(["delivered", "picked_up", "completed", "cancelled"]);

export default function OrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const load = useCallback(() => {
    api
      .order(Number(id))
      .then(setOrder)
      .catch((err) => setError(err.message));
  }, [id]);

  useEffect(load, [load]);

  // Poll while the order is still moving so status changes show up without a refresh.
  useEffect(() => {
    if (!order || FINAL.has(order.status)) return;
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  }, [order, load]);

  if (error) return <EmptyState emoji="🤷" title={error} />;
  if (!order) return <Spinner />;

  const cancel = async () => {
    if (!confirm("Cancel this order?")) return;
    setCancelling(true);
    try {
      setOrder(await api.cancelOrder(order.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't cancel");
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="page narrow">
      <Link to="/orders" className="small muted">
        ‹ All orders
      </Link>
      <OrderHero order={order} />

      <section className="card">
        <h3>Order status</h3>
        <ol className="timeline">
          {order.steps.map((step) => (
            <li key={step.status} className={`${step.done ? "done" : ""} ${step.status === "cancelled" ? "cancelled" : ""}`}>
              <span className="dot" />
              <span className="grow">{step.label}</span>
              {step.at && <span className="muted small">{timeLabel(step.at)}</span>}
            </li>
          ))}
        </ol>
      </section>

      <section className="card">
        <h3>
          {order.items.length} item{order.items.length > 1 ? "s" : ""} in this order
        </h3>
        {order.items.map((item) => (
          <div key={item.product_id} className="cart-line">
            <div className="cart-line-img">{item.emoji}</div>
            <div className="grow">
              <div className="cart-line-name">{item.name}</div>
              <div className="muted small">
                {item.unit} × {item.quantity}
                {order.fulfillment === "in_store" && item.location && ` · 📍 ${item.location.label}`}
              </div>
            </div>
            <strong>{rupees(item.price_paise * item.quantity)}</strong>
          </div>
        ))}
      </section>

      <BillDetails bill={order.bill} showDeliveryRows={order.fulfillment === "delivery"} />

      <section className="card small">
        <h3>Order details</h3>
        <p>
          <span className="muted">Order ID</span> #{order.id}
        </p>
        <p>
          <span className="muted">Placed</span> {dateTimeLabel(order.created_at)}
        </p>
        <p>
          <span className="muted">Payment</span> {order.payment_method.toUpperCase()} · {order.payment_status}
        </p>
        <p>
          <span className="muted">Store</span> {order.store.name}, {order.store.address}
        </p>
        {order.delivery_address && (
          <p>
            <span className="muted">Deliver to</span> {order.delivery_address}
          </p>
        )}
        {order.notes && (
          <p>
            <span className="muted">Instructions</span> {order.notes}
          </p>
        )}
      </section>

      {order.can_cancel && (
        <button className="btn btn-outline btn-block danger" onClick={cancel} disabled={cancelling}>
          {cancelling ? "Cancelling…" : "Cancel order"}
        </button>
      )}
    </div>
  );
}

function OrderHero({ order }: { order: Order }) {
  if (order.status === "cancelled") {
    return (
      <section className="order-hero cancelled">
        <h1>Order cancelled</h1>
        <p>{order.payment_status === "refunded" ? "Your refund has been processed." : "No payment was taken."}</p>
      </section>
    );
  }
  if (order.fulfillment === "delivery") {
    const delivered = order.status === "delivered";
    return (
      <section className="order-hero">
        <div className="order-hero-emoji">{delivered ? "✅" : "🛵"}</div>
        <h1>{delivered ? "Delivered" : order.status_label}</h1>
        {!delivered && order.eta_minutes && <p>Arriving in about {order.eta_minutes} minutes</p>}
      </section>
    );
  }
  if (order.fulfillment === "pickup") {
    return (
      <section className="order-hero pickup">
        <div className="order-hero-emoji">🏬</div>
        <h1>{order.status === "picked_up" ? "Picked up – thank you!" : order.status_label}</h1>
        {order.pickup_slot_start && order.pickup_slot_end && (
          <p>Pickup slot: {slotLabel(order.pickup_slot_start, order.pickup_slot_end)}</p>
        )}
        {order.status !== "picked_up" && (
          <div className="code-box">
            <small>Pickup code</small>
            <strong>{order.code}</strong>
            <small>Show this at the pickup counter of {order.store.name}</small>
          </div>
        )}
      </section>
    );
  }
  const paid = order.payment_status === "paid";
  return (
    <section className="order-hero instore">
      <div className="order-hero-emoji">{paid ? "✅" : "🧾"}</div>
      <h1>{paid ? "Paid – you're good to go!" : `Pay ${rupees(order.bill.total_paise)} at the counter`}</h1>
      <div className="code-box">
        <small>{paid ? "Exit pass" : "Bill code"}</small>
        <strong>{order.code}</strong>
        <small>{paid ? "Show this at the exit" : "Show this code to the cashier – no need to scan items again"}</small>
      </div>
    </section>
  );
}
