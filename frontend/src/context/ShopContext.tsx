import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { load, save } from "../lib/storage";
import type { Mode, Store } from "../lib/types";

export interface UserLocation {
  lat: number;
  lng: number;
  label: string;
}

export const PRESET_LOCATIONS: UserLocation[] = [
  { label: "Koramangala, Bengaluru", lat: 12.93, lng: 77.62 },
  { label: "Indiranagar, Bengaluru", lat: 12.978, lng: 77.64 },
  { label: "HSR Layout, Bengaluru", lat: 12.91, lng: 77.64 },
  { label: "BTM Layout, Bengaluru", lat: 12.9166, lng: 77.6101 },
  { label: "MG Road, Bengaluru", lat: 12.9756, lng: 77.6066 },
  { label: "Whitefield, Bengaluru", lat: 12.9698, lng: 77.75 },
];

interface ShopValue {
  mode: Mode;
  setMode: (mode: Mode) => void;
  location: UserLocation;
  setLocation: (location: UserLocation) => void;
  stores: Store[];
  /** Store that would deliver to `location`; null when the area isn't serviceable. */
  deliveryStore: Store | null;
  /** The store the current mode shops from (falls back to the closest one for browsing). */
  store: Store | null;
  selectStore: (storeId: number) => void;
  loading: boolean;
}

const ShopContext = createContext<ShopValue | null>(null);

export function ShopProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>(() => load<Mode>("smartcart.mode", "delivery"));
  const [location, setLocationState] = useState<UserLocation>(() =>
    load("smartcart.location", PRESET_LOCATIONS[0]),
  );
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(() => load("smartcart.store", null));
  const [stores, setStores] = useState<Store[]>([]);
  const [deliveryStore, setDeliveryStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      api.stores(location.lat, location.lng),
      api.nearestStore(location.lat, location.lng).catch(() => null),
    ])
      .then(([all, nearest]) => {
        if (cancelled) return;
        setStores(all);
        setDeliveryStore(nearest);
      })
      .catch(() => {
        if (!cancelled) setStores([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [location.lat, location.lng]);

  const store = useMemo(() => {
    if (mode === "delivery") return deliveryStore ?? stores[0] ?? null;
    return stores.find((s) => s.id === selectedStoreId) ?? stores[0] ?? null;
  }, [mode, deliveryStore, stores, selectedStoreId]);

  const value: ShopValue = {
    mode,
    setMode: (next) => {
      setModeState(next);
      save("smartcart.mode", next);
    },
    location,
    setLocation: (next) => {
      setLocationState(next);
      save("smartcart.location", next);
    },
    stores,
    deliveryStore,
    store,
    selectStore: (id) => {
      setSelectedStoreId(id);
      save("smartcart.store", id);
    },
    loading,
  };

  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>;
}

export function useShop(): ShopValue {
  const value = useContext(ShopContext);
  if (!value) throw new Error("useShop must be used inside <ShopProvider>");
  return value;
}
