import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { load, save } from "../lib/storage";
import type { CartItem, Product } from "../lib/types";
import { useShop } from "./ShopContext";

type Quantities = Record<number, number>;

interface Carts {
  // Delivery and pickup share one cart; the in-store shopping list is kept separately.
  online: Quantities;
  inStore: Quantities;
  products: Record<number, Product>;
}

interface CartValue {
  items: CartItem[];
  count: number;
  /** Client-side estimate from cached prices; the server quote is authoritative. */
  estimate: number;
  quantity: (productId: number) => number;
  add: (product: Product, by?: number) => void;
  setQuantity: (productId: number, quantity: number) => void;
  remember: (products: Product[]) => void;
  product: (productId: number) => Product | undefined;
  clear: () => void;
  isInStoreList: boolean;
  drawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
}

const MAX_QTY = 50;
const STORAGE_KEY = "smartcart.carts";
const CartContext = createContext<CartValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { mode } = useShop();
  const [carts, setCarts] = useState<Carts>(() => load(STORAGE_KEY, { online: {}, inStore: {}, products: {} }));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const key = mode === "in_store" ? "inStore" : "online";

  useEffect(() => save(STORAGE_KEY, carts), [carts]);

  const setQuantity = useCallback(
    (productId: number, quantity: number) =>
      setCarts((prev) => {
        const next = { ...prev[key] };
        if (quantity <= 0) delete next[productId];
        else next[productId] = Math.min(quantity, MAX_QTY);
        return { ...prev, [key]: next };
      }),
    [key],
  );

  const add = useCallback(
    (product: Product, by = 1) =>
      setCarts((prev) => {
        const current = prev[key][product.id] ?? 0;
        return {
          ...prev,
          products: { ...prev.products, [product.id]: product },
          [key]: { ...prev[key], [product.id]: Math.min(current + by, MAX_QTY) },
        };
      }),
    [key],
  );

  const remember = useCallback(
    (products: Product[]) =>
      setCarts((prev) => {
        const cache = { ...prev.products };
        for (const p of products) cache[p.id] = p;
        return { ...prev, products: cache };
      }),
    [],
  );

  const value = useMemo<CartValue>(() => {
    const active = carts[key];
    const items = Object.entries(active).map(([id, quantity]) => ({ product_id: Number(id), quantity }));
    return {
      items,
      count: items.reduce((sum, i) => sum + i.quantity, 0),
      estimate: items.reduce((sum, i) => sum + (carts.products[i.product_id]?.price_paise ?? 0) * i.quantity, 0),
      quantity: (id) => active[id] ?? 0,
      add,
      setQuantity,
      remember,
      product: (id) => carts.products[id],
      clear: () => setCarts((prev) => ({ ...prev, [key]: {} })),
      isInStoreList: key === "inStore",
      drawerOpen,
      openDrawer: () => setDrawerOpen(true),
      closeDrawer: () => setDrawerOpen(false),
    };
  }, [carts, key, add, setQuantity, remember, drawerOpen]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartValue {
  const value = useContext(CartContext);
  if (!value) throw new Error("useCart must be used inside <CartProvider>");
  return value;
}
