import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import BillDetails from "../components/BillDetails";
import { EmptyState, Spinner } from "../components/Loader";
import StoreModal from "../components/StoreModal";
import { useQuote } from "../hooks/useQuote";
import { api, ApiError } from "../lib/api";
import { rupees } from "../lib/format";
import type { Address, PaymentMethod, PickupDay } from "../lib/types";

const PAYMENT_OPTIONS: { id: PaymentMethod; label: (pickup: boolean) => string; note: string }[] = [
  { id: "upi", label: () => "UPI", note: "Simulated payment – marked paid instantly" },
  { id: "card", label: () => "Credit / Debit card", note: "Simulated payment – marked paid instantly" },
  { id: "cash", label: (pickup) => (pickup ? "Pay at store" : "Cash on delivery"), note: "Pay when you get your order" },
];

export default function Checkout() {
  const { user, requireLogin } = useAuth();
  const { mode, store, location, deliveryStore } = useShop();
  const cart = useCart();
  const navigate = useNavigate();
  const { quote } = useQuote(store?.id, mode, cart.items);

  const [addresses, setAddresses] = useState<Address[] | null>(null);
  const [addressId, setAddressId] = useState<number | null>(null);
  const [addingAddress, setAddingAddress] = useState(false);
  const [days, setDays] = useState<PickupDay[] | null>(null);
  const [dayIndex, setDayIndex] = useState(0);
  const [slot, setSlot] = useState<string | null>(null);
  const [payment, setPayment] = useState<PaymentMethod>("upi");
  const [notes, setNotes] = useState("");
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storePicker, setStorePicker] = useState(false);

  useEffect(() => {
    if (!user || mode !== "delivery") return;
    api.addresses().then((list) => {
      setAddresses(list);
      setAddressId((current) => current ?? list[0]?.id ?? null);
      if (list.length === 0) setAddingAddress(true);
    });
  }, [user, mode]);

  useEffect(() => {
    if (mode !== "pickup" || !store) return;
    setDays(null);
    setSlot(null);
    api.pickupSlots(store.id).then((res) => {
      setDays(res.days);
      setDayIndex(res.days.findIndex((d) => d.slots.some((s) => s.available)));
    });
  }, [mode, store?.id]);

  if (mode === "in_store") return <Navigate to="/in-store" replace />;
  if (!user) {
    return (
      <EmptyState emoji="🔐" title="Log in to check out">
        <button className="btn btn-primary" onClick={() => requireLogin()}>
          Login
        </button>
      </EmptyState>
    );
  }
  if (cart.items.length === 0) {
    return (
      <EmptyState emoji="🛒" title="Your cart is empty">
        <button className="btn btn-primary" onClick={() => navigate("/")}>
          Browse products
        </button>
      </EmptyState>
    );
  }

  const ready =
    quote?.can_checkout &&
    (mode === "delivery" ? addressId !== null && deliveryStore !== null : slot !== null) &&
    !placing;

  const place = async () => {
    if (!store) return;
    setPlacing(true);
    setError(null);
    try {
      const order = await api.placeOrder({
        store_id: store.id,
        fulfillment: mode,
        items: cart.items,
        payment_method: payment,
        address_id: mode === "delivery" ? (addressId ?? undefined) : undefined,
        pickup_slot_start: mode === "pickup" ? (slot ?? undefined) : undefined,
        notes: notes.trim() || undefined,
      });
      cart.clear();
      navigate(`/orders/${order.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't place the order");
      setPlacing(false);
    }
  };

  return (
    <div className="page checkout">
      <div className="checkout-main">
        <h1 className="page-title">{mode === "delivery" ? "Delivery details" : "Schedule your pickup"}</h1>

        {mode === "delivery" ? (
          <section className="card">
            <h3>Deliver to</h3>
            {addresses === null ? (
              <Spinner />
            ) : (
              <ul className="choice-list">
                {addresses.map((a) => (
                  <li key={a.id}>
                    <label className={`choice${a.id === addressId ? " selected" : ""}`}>
                      <input
                        type="radio"
                        name="address"
                        checked={a.id === addressId}
                        onChange={() => setAddressId(a.id)}
                      />
                      <span className="grow">
                        <strong>{a.label}</strong>
                        <span className="muted small block">
                          {[a.line1, a.line2, a.landmark, a.city, a.pincode].filter(Boolean).join(", ")}
                        </span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
            {addingAddress ? (
              <AddressForm
                defaults={location}
                onCancel={addresses?.length ? () => setAddingAddress(false) : undefined}
                onSaved={(a) => {
                  setAddresses((list) => [a, ...(list ?? [])]);
                  setAddressId(a.id);
                  setAddingAddress(false);
                }}
              />
            ) : (
              <button className="link-btn" onClick={() => setAddingAddress(true)}>
                + Add a new address
              </button>
            )}
            {deliveryStore ? (
              <p className="small">
                ⏱ Arrives in about <strong>{deliveryStore.delivery_eta_minutes} minutes</strong> from {deliveryStore.name}
              </p>
            ) : (
              <p className="error-text">We don't deliver to your selected location yet.</p>
            )}
          </section>
        ) : (
          <section className="card">
            <div className="row-between">
              <div>
                <h3>Pickup store</h3>
                <strong>{store?.name}</strong>
                <div className="muted small">{store?.address}</div>
              </div>
              <button className="btn btn-outline" onClick={() => setStorePicker(true)}>
                Change
              </button>
            </div>
            <h3 style={{ marginTop: 20 }}>Pickup slot</h3>
            {days === null ? (
              <Spinner />
            ) : (
              <>
                <div className="tabs">
                  {days.map((d, i) => (
                    <button key={d.date} className={i === dayIndex ? "active" : ""} onClick={() => setDayIndex(i)}>
                      {d.label}
                    </button>
                  ))}
                </div>
                {days[dayIndex]?.slots.length ? (
                  <div className="slot-grid">
                    {days[dayIndex].slots.map((s) => (
                      <button
                        key={s.start}
                        disabled={!s.available}
                        className={`slot${slot === s.start ? " selected" : ""}`}
                        onClick={() => setSlot(s.start)}
                      >
                        {s.label}
                        <small>{s.available ? `${s.remaining} left` : "Full"}</small>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="muted">No slots left for this day.</p>
                )}
              </>
            )}
          </section>
        )}

        <section className="card">
          <h3>Payment</h3>
          <ul className="choice-list">
            {PAYMENT_OPTIONS.map((opt) => (
              <li key={opt.id}>
                <label className={`choice${payment === opt.id ? " selected" : ""}`}>
                  <input type="radio" name="pay" checked={payment === opt.id} onChange={() => setPayment(opt.id)} />
                  <span className="grow">
                    <strong>{opt.label(mode === "pickup")}</strong>
                    <span className="muted small block">{opt.note}</span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <label className="field">
            <span>Instructions (optional)</span>
            <input
              value={notes}
              maxLength={500}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={mode === "delivery" ? "e.g. Don't ring the bell" : "e.g. Please pack separately"}
            />
          </label>
        </section>
      </div>

      <aside className="checkout-side">
        <section className="card">
          <h3>
            {cart.count} item{cart.count > 1 ? "s" : ""}
          </h3>
          {quote?.lines.map((l) => (
            <div key={l.product.id} className="summary-line small">
              <span>
                {l.product.emoji} {l.product.name} × {l.quantity}
              </span>
              <span>{rupees(l.line_total_paise)}</span>
            </div>
          ))}
        </section>
        {quote && <BillDetails bill={quote.bill} showDeliveryRows={mode === "delivery"} />}
        {quote?.issues.map((i) => (
          <p key={i} className="error-text">
            ⚠️ {i}
          </p>
        ))}
        {error && <p className="error-text">{error}</p>}
        <button className="checkout-btn" disabled={!ready} onClick={place}>
          <span>
            <strong>{rupees(quote?.bill.total_paise ?? cart.estimate)}</strong>
            <small>TOTAL</small>
          </span>
          <span>{placing ? "Placing…" : mode === "pickup" && !slot ? "Choose a slot" : "Place order"} ›</span>
        </button>
      </aside>
      {storePicker && <StoreModal onClose={() => setStorePicker(false)} />}
    </div>
  );
}

function AddressForm({
  defaults,
  onSaved,
  onCancel,
}: {
  defaults: { lat: number; lng: number; label: string };
  onSaved: (a: Address) => void;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState({ label: "Home", line1: "", landmark: "", city: "Bengaluru", pincode: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onSaved(
        await api.addAddress({
          ...form,
          line2: null,
          landmark: form.landmark || null,
          lat: defaults.lat,
          lng: defaults.lng,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save address");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="address-form" onSubmit={submit}>
      <p className="muted small">📍 Pinned at {defaults.label}</p>
      <div className="tabs">
        {["Home", "Work", "Other"].map((l) => (
          <button type="button" key={l} className={form.label === l ? "active" : ""} onClick={() => setForm({ ...form, label: l })}>
            {l}
          </button>
        ))}
      </div>
      <label className="field">
        <span>Flat / House no. / Building *</span>
        <input required minLength={3} value={form.line1} onChange={set("line1")} />
      </label>
      <label className="field">
        <span>Landmark</span>
        <input value={form.landmark} onChange={set("landmark")} />
      </label>
      <div className="field-row">
        <label className="field">
          <span>City *</span>
          <input required value={form.city} onChange={set("city")} />
        </label>
        <label className="field">
          <span>Pincode *</span>
          <input required pattern="\d{6}" inputMode="numeric" maxLength={6} value={form.pincode} onChange={set("pincode")} />
        </label>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="row-gap">
        <button className="btn btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save address"}
        </button>
        {onCancel && (
          <button type="button" className="btn btn-outline" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
