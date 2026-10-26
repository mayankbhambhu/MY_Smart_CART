import { useState } from "react";
import { PRESET_LOCATIONS, useShop } from "../context/ShopContext";
import Modal from "./Modal";

export default function LocationModal({ onClose }: { onClose: () => void }) {
  const { location, setLocation } = useShop();
  const [error, setError] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);

  const useCurrent = () => {
    if (!navigator.geolocation) {
      setError("Location isn't available in this browser");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: "Current location" });
        onClose();
      },
      () => {
        setLocating(false);
        setError("We couldn't get your location. Pick an area below.");
      },
      { timeout: 10000 },
    );
  };

  return (
    <Modal title="Change location" onClose={onClose}>
      <button className="btn btn-outline btn-block" onClick={useCurrent} disabled={locating}>
        📍 {locating ? "Detecting…" : "Use my current location"}
      </button>
      {error && <p className="error-text">{error}</p>}
      <p className="muted small" style={{ margin: "16px 0 8px" }}>
        Or choose an area
      </p>
      <ul className="choice-list">
        {PRESET_LOCATIONS.map((preset) => (
          <li key={preset.label}>
            <button
              className={`choice${preset.label === location.label ? " selected" : ""}`}
              onClick={() => {
                setLocation(preset);
                onClose();
              }}
            >
              <span>🏠</span>
              <span>{preset.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </Modal>
  );
}
