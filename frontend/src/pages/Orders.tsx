import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { EmptyState, Spinner } from "../components/Loader";
import { api } from "../lib/api";
import { dateTimeLabel, MODE_LABELS, rupees } from "../lib/format";
import type { Order } from "../lib/types";

export default function Orders() {
  const { user, requireLogin } = useAuth();
  const [orders, setOrders] = useState<Order[] | null>(null);

  useEffect(() => {
    if (user) api.orders().then(setOrders);
  }, [user]);

  if (!user) {
    return (
      <EmptyState emoji="📦" title="Log in to see your orders">
        <button className="btn btn-primary" onClick={() => requireLogin()}>
          Login
        </button>
      </EmptyState>
    );
  }
  if (orders === null) return <Spinner />;
  if (orders.length === 0) {
    return (
      <EmptyState emoji="📦" title="No orders yet">
        <Link to="/" className="btn btn-primary">
          Start shopping
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="page narrow">
      <h1 className="page-title">My orders</h1>
      {orders.map((o) => (
        <Link key={o.id} to={`/orders/${o.id}`} className="card order-row">
          <div className="order-row-emojis" aria-hidden>
            {o.items.slice(0, 3).map((i) => i.emoji).join("")}
          </div>
          <div className="grow">
            <strong>
              {MODE_LABELS[o.fulfillment]} · {rupees(o.bill.total_paise)}
            </strong>
            <div className="muted small">
              #{o.id} · {dateTimeLabel(o.created_at)} · {o.store.name}
            </div>
          </div>
          <span className={`status-pill status-${o.status}`}>{o.status_label}</span>
        </Link>
      ))}
    </div>
  );
}
