export function rupees(paise: number): string {
  const value = paise / 100;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: Number.isInteger(value) ? 0 : 2 })}`;
}

export function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}

export function dateTimeLabel(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Store hours and pickup slots are in the store's local time (all demo stores are in India).
const STORE_TZ = "Asia/Kolkata";

export function slotLabel(start: string, end: string): string {
  const day = new Date(start).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: STORE_TZ,
  });
  const time = (iso: string) =>
    new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: STORE_TZ });
  return `${day}, ${time(start)} – ${time(end)}`;
}

export const MODE_LABELS = {
  delivery: "Delivery",
  pickup: "Pickup",
  in_store: "In-store",
} as const;
