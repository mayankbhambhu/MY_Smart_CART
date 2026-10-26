import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { CartItem, Mode, Quote } from "../lib/types";

/** Live server-side pricing for the cart, refreshed (debounced) whenever it changes. */
export function useQuote(storeId: number | undefined, mode: Mode, items: CartItem[], enabled = true) {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(items);

  useEffect(() => {
    if (!enabled || !storeId || items.length === 0) {
      setQuote(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      api
        .quote(storeId, mode, items)
        .then((q) => !cancelled && (setQuote(q), setError(null)))
        .catch((err) => !cancelled && setError(err.message));
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [storeId, mode, key, enabled]);

  return { quote, error };
}
