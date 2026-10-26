import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useShop } from "../context/ShopContext";
import AddButton from "../components/AddButton";
import { EmptyState, Spinner } from "../components/Loader";
import Modal from "../components/Modal";
import StoreMap from "../components/StoreMap";
import StoreModal from "../components/StoreModal";
import { api, ApiError } from "../lib/api";
import { rupees } from "../lib/format";
import { load, save } from "../lib/storage";
import type { InStoreLine, InStoreRoute, PaymentMethod, Product } from "../lib/types";

const EXAMPLES = ["2 milk, brown bread and a dozen eggs", "1 kg onion, tomatoes, coriander", "atta, toor dal, tata salt"];

// Minimal typing for the Web Speech API (Chrome/Edge/Safari expose it with a webkit prefix).
interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
}
type RecognitionCtor = new () => Recognition;

function speechRecognition(): RecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export default function InStore() {
  const { mode, setMode, store } = useShop();
  const cart = useCart();
  const { requireLogin } = useAuth();
  const navigate = useNavigate();

  const [text, setText] = useState("");
  const [finding, setFinding] = useState(false);
  const [unmatched, setUnmatched] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [alternatives, setAlternatives] = useState<Record<number, Product[]>>({});
  const [route, setRoute] = useState<InStoreRoute | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [listening, setListening] = useState(false);
  const [storePicker, setStorePicker] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [focus, setFocus] = useState<number | null>(null);
  const recognition = useRef<Recognition | null>(null);
  const pickedKey = `smartcart.picked.${store?.id}`;

  useEffect(() => {
    if (mode !== "in_store") setMode("in_store");
  }, [mode, setMode]);

  useEffect(() => {
    setPicked(new Set(load<number[]>(pickedKey, [])));
  }, [pickedKey]);

  const itemsKey = JSON.stringify(cart.items);
  useEffect(() => {
    if (!store || mode !== "in_store") return;
    if (cart.items.length === 0) {
      setRoute(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      api.shoppingRoute(store.id, cart.items).then((r) => !cancelled && setRoute(r));
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [store?.id, itemsKey, mode]);

  const findItems = async (input: string) => {
    if (!store || !input.trim()) return;
    setFinding(true);
    setMessage(null);
    try {
      const res = await api.matchList(store.id, input);
      for (const match of res.matches) cart.add(match.product, match.quantity);
      setAlternatives((prev) => {
        const next = { ...prev };
        for (const m of res.matches) next[m.product.id] = m.alternatives;
        return next;
      });
      setUnmatched(res.unmatched);
      if (res.matches.length) {
        setMessage(`Added ${res.matches.length} item${res.matches.length > 1 ? "s" : ""} to your list`);
        setText("");
      }
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Couldn't look up your list");
    } finally {
      setFinding(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    findItems(text);
  };

  const toggleListening = () => {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const Ctor = speechRecognition();
    if (!Ctor) {
      setMessage("Voice input isn't supported in this browser. Try Chrome, or type your list.");
      return;
    }
    const rec = new Ctor();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    let transcript = "";
    rec.onresult = (e) => {
      transcript = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join(" ");
      setText(transcript);
    };
    rec.onerror = (e) => setMessage(e.error === "not-allowed" ? "Microphone permission was denied" : "Didn't catch that");
    rec.onend = () => {
      setListening(false);
      if (transcript.trim()) findItems(transcript);
    };
    recognition.current = rec;
    setListening(true);
    setMessage(null);
    rec.start();
  };

  const togglePicked = (productId: number) => {
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(productId)) next.delete(productId);
      else next.add(productId);
      save(pickedKey, [...next]);
      return next;
    });
  };

  const swap = (from: InStoreLine, to: Product) => {
    cart.setQuantity(from.product.id, 0);
    cart.add(to, from.quantity);
    setAlternatives((prev) => ({ ...prev, [to.id]: [from.product, ...(prev[from.product.id] ?? []).filter((p) => p.id !== to.id)] }));
  };

  const groups = useMemo(() => {
    const out: { aisle: number; name: string; lines: { line: InStoreLine; stop: number }[] }[] = [];
    route?.lines.forEach((line, index) => {
      const loc = line.product.location;
      if (!loc) return;
      const last = out[out.length - 1];
      if (last && last.aisle === loc.aisle_number) last.lines.push({ line, stop: index + 1 });
      else out.push({ aisle: loc.aisle_number, name: loc.aisle_name, lines: [{ line, stop: index + 1 }] });
    });
    return out;
  }, [route]);

  if (!store) return <Spinner label="Loading stores…" />;

  const pickedCount = route?.lines.filter((l) => picked.has(l.product.id)).length ?? 0;
  const lineCount = route?.lines.length ?? 0;
  // Sold-out items stay on the list (so you can swap them) but can't be bought.
  const canCheckout = route?.lines.some((l) => l.available_quantity > 0) ?? false;

  return (
    <div className="page instore">
      <section className="instore-head card">
        <div>
          <div className="muted small">You're shopping at</div>
          <h1>{store.name}</h1>
          <div className="small">
            <span className={store.is_open ? "open-dot" : "closed-dot"} /> {store.is_open ? "Open now" : "Closed"} ·{" "}
            {store.address}
          </div>
        </div>
        <button className="btn btn-outline" onClick={() => setStorePicker(true)}>
          Change store
        </button>
      </section>

      <div className="instore-layout">
        <div className="instore-main">
          <form className="card list-input" onSubmit={onSubmit}>
            <h2>What do you want to buy?</h2>
            <p className="muted small">
              Type or say your list – we'll find each item's aisle and row and add up your total.
            </p>
            <div className="list-input-row">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    findItems(text);
                  }
                }}
                rows={2}
                placeholder='e.g. "2 milk, brown bread and a dozen eggs"'
                aria-label="Shopping list"
              />
              <button
                type="button"
                className={`mic-btn${listening ? " listening" : ""}`}
                onClick={toggleListening}
                aria-label={listening ? "Stop listening" : "Speak your list"}
                title={listening ? "Stop listening" : "Speak your list"}
              >
                {listening ? "■" : "🎤"}
              </button>
            </div>
            <div className="row-between wrap">
              <div className="chips">
                {EXAMPLES.map((ex) => (
                  <button type="button" key={ex} className="chip" onClick={() => findItems(ex)}>
                    {ex}
                  </button>
                ))}
              </div>
              <button className="btn btn-primary" disabled={finding || !text.trim()}>
                {finding ? "Finding…" : "Find items"}
              </button>
            </div>
            {listening && <p className="listening-text">🎙️ Listening… say something like "two milk and bread"</p>}
            {message && <p className="small">{message}</p>}
            {unmatched.length > 0 && (
              <p className="error-text">
                Couldn't find: {unmatched.map((u) => `"${u}"`).join(", ")}. Try another name, or ask a store assistant.
              </p>
            )}
          </form>

          {cart.items.length === 0 ? (
            <EmptyState emoji="📝" title="Your shopping list is empty">
              <p className="muted">Add items above, or browse the catalogue – every product shows its aisle.</p>
            </EmptyState>
          ) : !route ? (
            <Spinner label="Mapping your route…" />
          ) : (
            <section className="card route">
              <div className="row-between">
                <h2>Your route</h2>
                <span className="muted small">
                  {pickedCount}/{lineCount} in basket
                </span>
              </div>
              <div className="progress" aria-hidden>
                <span style={{ width: `${lineCount ? (pickedCount / lineCount) * 100 : 0}%` }} />
              </div>
              {groups.map((group) => (
                <div key={group.aisle} className="route-group">
                  <div className="route-aisle">
                    <span className="aisle-badge">Aisle {group.aisle}</span>
                    <span>{group.name}</span>
                  </div>
                  {group.lines.map(({ line, stop }) => {
                    const done = picked.has(line.product.id);
                    const alts = (alternatives[line.product.id] ?? []).filter((p) => p.in_stock);
                    return (
                      <div
                        key={line.product.id}
                        className={`route-line${done ? " done" : ""}`}
                        onMouseEnter={() => setFocus(line.product.id)}
                        onMouseLeave={() => setFocus(null)}
                      >
                        <button
                          className="check"
                          onClick={() => togglePicked(line.product.id)}
                          aria-label={done ? "Mark as not picked" : "Mark as picked"}
                          aria-pressed={done}
                        >
                          {done ? "✓" : stop}
                        </button>
                        <span className="route-emoji" aria-hidden>
                          {line.product.emoji}
                        </span>
                        <div className="grow">
                          <div className="route-name">{line.product.name}</div>
                          <div className="route-loc">
                            📍 <strong>{line.product.location?.label}</strong> · {line.product.unit}
                            {line.available_quantity === 0 ? (
                              <span className="error-text"> · Out of stock – not in total</span>
                            ) : (
                              line.available_quantity < line.quantity && (
                                <span className="error-text"> · Only {line.available_quantity} left</span>
                              )
                            )}
                          </div>
                          {alts.length > 0 && (
                            <select
                              className="swap"
                              value=""
                              onChange={(e) => {
                                const to = alts.find((p) => p.id === Number(e.target.value));
                                if (to) swap(line, to);
                              }}
                              aria-label="Swap for a similar product"
                            >
                              <option value="">Not this one? Swap…</option>
                              {alts.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.name} ({p.unit}) – {rupees(p.price_paise)} · {p.location?.label}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                        <div className="route-right">
                          <strong>{rupees(line.line_total_paise)}</strong>
                          <AddButton product={line.product} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
              {route.issues.map((issue) => (
                <p key={issue} className="error-text">
                  ⚠️ {issue}
                </p>
              ))}
              <button className="link-btn danger" onClick={() => (cart.clear(), setPicked(new Set()), save(pickedKey, []))}>
                Clear list
              </button>
            </section>
          )}
        </div>

        <aside className="instore-side">
          {route && route.lines.length > 0 && (
            <section className="card">
              <h3>Store map</h3>
              <StoreMap aisles={route.store.aisles} lines={route.lines} picked={picked} focus={focus} />
            </section>
          )}
          {route && route.lines.length > 0 && (
            <section className="card total-card">
              <div className="row-between">
                <span>
                  {cart.count} item{cart.count > 1 ? "s" : ""}
                </span>
                {route.bill.savings_paise > 0 && (
                  <span className="free small">You save {rupees(route.bill.savings_paise)}</span>
                )}
              </div>
              <div className="total-amount">
                <small>Total amount</small>
                <strong>{rupees(route.bill.total_paise)}</strong>
                {route.bill.savings_paise > 0 && <s className="muted">{rupees(route.bill.mrp_total_paise)}</s>}
              </div>
              <button
                className="btn btn-primary btn-block"
                disabled={!canCheckout}
                onClick={() => requireLogin(() => setCheckoutOpen(true))}
              >
                Done shopping – checkout ›
              </button>
              <p className="muted small">No delivery or handling fees when you shop in the store.</p>
            </section>
          )}
        </aside>
      </div>

      {route && route.lines.length > 0 && (
        <div className="instore-bar">
          <span>
            <small>
              {pickedCount}/{lineCount} picked · Total
            </small>
            <strong>{rupees(route.bill.total_paise)}</strong>
          </span>
          <button
            className="btn btn-primary"
            disabled={!canCheckout}
            onClick={() => requireLogin(() => setCheckoutOpen(true))}
          >
            Checkout ›
          </button>
        </div>
      )}

      {storePicker && <StoreModal onClose={() => setStorePicker(false)} />}
      {checkoutOpen && route && (
        <InStoreCheckout
          route={route}
          onClose={() => setCheckoutOpen(false)}
          onPlaced={(orderId) => {
            cart.clear();
            save(pickedKey, []);
            navigate(`/orders/${orderId}`);
          }}
        />
      )}
    </div>
  );
}

function InStoreCheckout({
  route,
  onClose,
  onPlaced,
}: {
  route: InStoreRoute;
  onClose: () => void;
  onPlaced: (orderId: number) => void;
}) {
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const place = async () => {
    setBusy(true);
    setError(null);
    try {
      const order = await api.placeOrder({
        store_id: route.store.id,
        fulfillment: "in_store",
        items: route.lines
          .filter((l) => l.available_quantity > 0)
          .map((l) => ({ product_id: l.product.id, quantity: l.available_quantity })),
        payment_method: method,
      });
      onPlaced(order.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't check out");
      setBusy(false);
    }
  };

  return (
    <Modal title="Checkout" onClose={onClose}>
      <p>
        {route.lines.filter((l) => l.available_quantity > 0).length} products ·{" "}
        <strong>{rupees(route.bill.total_paise)}</strong>
      </p>
      {route.issues.length > 0 && <p className="muted small">Sold-out items are left off your bill.</p>}
      <ul className="choice-list">
        <li>
          <label className={`choice${method === "cash" ? " selected" : ""}`}>
            <input type="radio" checked={method === "cash"} onChange={() => setMethod("cash")} />
            <span className="grow">
              <strong>Pay at the counter</strong>
              <span className="muted small block">Get a bill code – the cashier pulls up your bill instantly</span>
            </span>
          </label>
        </li>
        <li>
          <label className={`choice${method === "upi" ? " selected" : ""}`}>
            <input type="radio" checked={method === "upi"} onChange={() => setMethod("upi")} />
            <span className="grow">
              <strong>Pay now with UPI (scan &amp; go)</strong>
              <span className="muted small block">Simulated payment – show the exit pass and walk out</span>
            </span>
          </label>
        </li>
      </ul>
      {error && <p className="error-text">{error}</p>}
      <button className="btn btn-primary btn-block" onClick={place} disabled={busy}>
        {busy ? "Generating…" : method === "cash" ? "Get my bill code" : `Pay ${rupees(route.bill.total_paise)}`}
      </button>
    </Modal>
  );
}
