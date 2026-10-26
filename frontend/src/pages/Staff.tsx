import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { useShop } from "../context/ShopContext";
import { EmptyState, Spinner } from "../components/Loader";
import { api, ApiError } from "../lib/api";
import { MODE_LABELS, rupees, slotLabel, timeLabel } from "../lib/format";
import type { StaffOrder } from "../lib/types";

export default function Staff() {
  const { user, requireLogin } = useAuth();
  const { stores } = useShop();
  const [storeId, setStoreId] = useState<number | null>(null);
  const [orders, setOrders] = useState<StaffOrder[] | null>(null);
  const [code, setCode] = useState("");
  const [found, setFound] = useState<StaffOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeStore = storeId ?? stores[0]?.id ?? null;
  const isStaff = user?.role === "staff";

  const refresh = useCallback(() => {
    if (!activeStore || !isStaff) return;
    api.staffOrders(activeStore).then(setOrders).catch((err) => setError(err.message));
  }, [activeStore, isStaff]);

  useEffect(() => {
    setOrders(null);
    refresh();
    const timer = setInterval(refresh, 10000);
    return () => clearInterval(timer);
  }, [refresh]);

  if (!user) {
    return (
      <EmptyState emoji="🏪" title="Store staff login">
        <p className="muted">Use the demo staff number 9999999999.</p>
        <button className="btn btn-primary" onClick={() => requireLogin()}>
          Login
        </button>
      </EmptyState>
    );
  }
  if (!isStaff) return <EmptyState emoji="⛔" title="This page is for store staff only" />;

  const advance = async (order: StaffOrder) => {
    try {
      const updated = await api.advanceOrder(order.id);
      if (found?.id === updated.id) setFound(updated);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update order");
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    if (!activeStore) return;
    setError(null);
    setFound(null);
    try {
      setFound(await api.verifyCode(activeStore, code));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lookup failed");
    }
  };

  return (
    <div className="page">
      <div className="row-between wrap">
        <h1 className="page-title">Store dashboard</h1>
        <select
          value={activeStore ?? ""}
          onChange={(e) => setStoreId(Number(e.target.value))}
          aria-label="Store"
          className="select"
        >
          {stores.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      <form className="card verify" onSubmit={verify}>
        <h3>Verify pickup OTP / in-store bill code</h3>
        <div className="row-gap">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="e.g. 4821 or K7P2QX"
            maxLength={12}
            aria-label="Customer code"
          />
          <button className="btn btn-primary" disabled={code.trim().length < 4}>
            Look up
          </button>
        </div>
        {found && <StaffOrderCard order={found} onAdvance={advance} highlight />}
      </form>
      {error && <p className="error-text">{error}</p>}

      <h2 className="section-title">Active orders</h2>
      {orders === null ? (
        <Spinner />
      ) : orders.length === 0 ? (
        <EmptyState emoji="☕" title="No active orders right now" />
      ) : (
        <div className="staff-grid">
          {orders.map((o) => (
            <StaffOrderCard key={o.id} order={o} onAdvance={advance} />
          ))}
        </div>
      )}
    </div>
  );
}

function StaffOrderCard({
  order,
  onAdvance,
  highlight,
}: {
  order: StaffOrder;
  onAdvance: (o: StaffOrder) => void;
  highlight?: boolean;
}) {
  return (
    <div className={`card staff-card${highlight ? " highlight" : ""}`}>
      <div className="row-between">
        <strong>
          #{order.id} · {MODE_LABELS[order.fulfillment]}
        </strong>
        <span className={`status-pill status-${order.status}`}>{order.status_label}</span>
      </div>
      <div className="muted small">
        {order.customer_name ?? "Customer"} · +91 {order.customer_phone} · placed {timeLabel(order.created_at)}
      </div>
      {order.pickup_slot_start && order.pickup_slot_end && (
        <div className="small">🕒 {slotLabel(order.pickup_slot_start, order.pickup_slot_end)}</div>
      )}
      {order.delivery_address && <div className="small">📍 {order.delivery_address}</div>}
      <ul className="pick-list">
        {order.items.map((i) => (
          <li key={i.product_id}>
            <span>
              {i.emoji} {i.name} <span className="muted">({i.unit})</span> × <strong>{i.quantity}</strong>
            </span>
            {i.location && <span className="aisle-chip">{i.location.label}</span>}
          </li>
        ))}
      </ul>
      <div className="row-between">
        <span>
          <strong>{rupees(order.bill.total_paise)}</strong>{" "}
          <span className="muted small">
            {order.payment_method.toUpperCase()} · {order.payment_status}
          </span>
        </span>
        {order.next_status_label && (
          <button className="btn btn-primary" onClick={() => onAdvance(order)}>
            Mark {order.next_status_label.toLowerCase()}
          </button>
        )}
      </div>
    </div>
  );
}
