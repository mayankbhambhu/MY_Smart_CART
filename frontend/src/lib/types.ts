// Mirrors backend/app/schemas.py. All money values are integer paise (₹1 = 100 paise).

export type Mode = "delivery" | "pickup" | "in_store";
export type PaymentMethod = "cash" | "upi" | "card";
export type PaymentStatus = "pending" | "paid" | "refunded";
export type OrderStatus =
  | "placed"
  | "packed"
  | "out_for_delivery"
  | "delivered"
  | "ready_for_pickup"
  | "picked_up"
  | "awaiting_payment"
  | "completed"
  | "cancelled";

export interface User {
  id: number;
  phone: string;
  name: string | null;
  email: string | null;
  role: "customer" | "staff";
}

export interface Address {
  id: number;
  label: string;
  line1: string;
  line2: string | null;
  landmark: string | null;
  city: string;
  pincode: string;
  lat: number;
  lng: number;
}

export type AddressInput = Omit<Address, "id">;

export interface Store {
  id: number;
  name: string;
  address: string;
  city: string;
  lat: number;
  lng: number;
  opens_at: string;
  closes_at: string;
  is_open: boolean;
  distance_km: number | null;
  delivers_here: boolean | null;
  delivery_eta_minutes: number | null;
}

export interface Aisle {
  number: number;
  name: string;
  row_count: number;
}

export interface StoreLayout extends Store {
  aisles: Aisle[];
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  emoji: string;
  color: string;
}

export interface ItemLocation {
  aisle_number: number;
  aisle_name: string;
  row_number: number;
  label: string;
}

export interface Product {
  id: number;
  category_id: number;
  name: string;
  brand: string | null;
  unit: string;
  description: string | null;
  mrp_paise: number;
  price_paise: number;
  discount_percent: number;
  emoji: string;
  image_url: string | null;
  in_stock: boolean;
  stock: number | null;
  location: ItemLocation | null;
}

export interface CategoryWithProducts extends Category {
  products: Product[];
}

export interface CartItem {
  product_id: number;
  quantity: number;
}

export interface Bill {
  item_total_paise: number;
  mrp_total_paise: number;
  savings_paise: number;
  delivery_fee_paise: number;
  handling_fee_paise: number;
  small_cart_fee_paise: number;
  total_paise: number;
  free_delivery_threshold_paise: number | null;
  amount_to_free_delivery_paise: number | null;
}

export interface QuoteLine {
  product: Product;
  quantity: number;
  available_quantity: number;
  line_total_paise: number;
  line_mrp_paise: number;
}

export interface Quote {
  store_id: number;
  fulfillment: Mode;
  lines: QuoteLine[];
  bill: Bill;
  issues: string[];
  can_checkout: boolean;
}

export interface PickupSlot {
  start: string;
  end: string;
  label: string;
  remaining: number;
  available: boolean;
}

export interface PickupDay {
  date: string;
  label: string;
  slots: PickupSlot[];
}

export interface InStoreMatch {
  query: string;
  quantity: number;
  product: Product;
  alternatives: Product[];
}

export interface InStoreMatchResponse {
  matches: InStoreMatch[];
  unmatched: string[];
}

export interface InStoreLine {
  product: Product;
  quantity: number;
  available_quantity: number;
  line_total_paise: number;
  line_mrp_paise: number;
}

export interface InStoreRoute {
  store: StoreLayout;
  lines: InStoreLine[];
  bill: Bill;
  issues: string[];
}

export interface OrderItem {
  product_id: number;
  name: string;
  unit: string;
  emoji: string;
  price_paise: number;
  mrp_paise: number;
  quantity: number;
  location: ItemLocation | null;
}

export interface OrderStep {
  status: OrderStatus;
  label: string;
  done: boolean;
  at: string | null;
}

export interface Order {
  id: number;
  store: { id: number; name: string; address: string };
  fulfillment: Mode;
  status: OrderStatus;
  status_label: string;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  delivery_address: string | null;
  eta_minutes: number | null;
  pickup_slot_start: string | null;
  pickup_slot_end: string | null;
  code: string | null;
  notes: string | null;
  bill: Bill;
  items: OrderItem[];
  steps: OrderStep[];
  can_cancel: boolean;
  created_at: string;
}

export interface StaffOrder extends Order {
  customer_phone: string;
  customer_name: string | null;
  next_status: OrderStatus | null;
  next_status_label: string | null;
}

export interface OrderCreate {
  store_id: number;
  fulfillment: Mode;
  items: CartItem[];
  payment_method: PaymentMethod;
  address_id?: number;
  pickup_slot_start?: string;
  notes?: string;
}
