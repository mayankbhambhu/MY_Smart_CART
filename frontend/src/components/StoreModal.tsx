import { useShop } from "../context/ShopContext";
import Modal from "./Modal";

export default function StoreModal({ onClose }: { onClose: () => void }) {
  const { stores, store, selectStore, mode } = useShop();
  return (
    <Modal title={mode === "pickup" ? "Pick up from" : "Which store are you in?"} onClose={onClose}>
      <ul className="choice-list">
        {stores.map((s) => (
          <li key={s.id}>
            <button
              className={`choice store-choice${s.id === store?.id ? " selected" : ""}`}
              onClick={() => {
                selectStore(s.id);
                onClose();
              }}
            >
              <span className="store-icon">🏬</span>
              <span className="grow">
                <strong>{s.name}</strong>
                <span className="muted small block">{s.address}</span>
                <span className="small block">
                  <span className={s.is_open ? "open-dot" : "closed-dot"} /> {s.is_open ? "Open" : "Closed"} ·{" "}
                  {s.opens_at === "00:00" && s.closes_at === "24:00" ? "24 hours" : `${s.opens_at}–${s.closes_at}`}
                  {s.distance_km != null && ` · ${s.distance_km.toFixed(1)} km away`}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </Modal>
  );
}
