// Mirrors the FastAPI response models in backend/app/schemas.

export type FulfillmentType = 'delivery' | 'pickup' | 'in_store'
export type OrderStatus =
  | 'payment_pending'
  | 'placed'
  | 'confirmed'
  | 'packing'
  | 'out_for_delivery'
  | 'delivered'
  | 'ready_for_pickup'
  | 'picked_up'
  | 'awaiting_payment'
  | 'completed'
  | 'cancelled'
export type PaymentMethod = 'cod' | 'pay_at_store' | 'online'
export type PaymentStatus = 'pending' | 'paid' | 'refunded'
export type PaymentState = 'created' | 'paid' | 'failed' | 'refunded'
export type UserRole = 'customer' | 'staff' | 'admin'

export interface User {
  id: number
  phone: string
  name: string | null
  email: string | null
  role: UserRole
  store_id: number | null
}

export interface AppConfig {
  app_name: string
  business: { legal_name: string | null; support_email: string | null; support_phone: string | null }
  /** 'screen': demo deployment, the code is shown on the login screen instead of sent by SMS. */
  otp_delivery: 'sms' | 'screen'
  payments: {
    online: boolean
    provider: 'razorpay' | 'simulated' | null
    key_id: string | null
    test_mode: boolean
  }
  payment_timeout_minutes: number
  demo: boolean
}

export interface OtpRequestResult {
  phone: string
  expires_in: number
  resend_in: number
  delivery: 'sms' | 'screen'
  dev_otp: string | null
}

export interface Session {
  access_token: string
  token_type: string
  user: User
  is_new_user: boolean
}

export interface Category {
  id: number
  name: string
  slug: string
  parent_id: number | null
  emoji: string
  image_url: string | null
  color: string
}

export interface CategoryTree extends Category {
  children: Category[]
}

export interface ShelfLocation {
  aisle: number
  aisle_name: string | null
  row: number
  label: string
}

export interface Availability {
  in_stock: boolean
  stock: number
  max_qty: number
}

export interface Product {
  id: number
  name: string
  slug: string
  brand: string | null
  unit_label: string
  price: number
  mrp: number
  discount_percent: number
  emoji: string
  image_url: string | null
  is_veg: boolean
  category_id: number
  availability: Availability | null
  location: ShelfLocation | null
}

export interface ProductDetail extends Product {
  description: string | null
  tags: string[]
  category: Category
  parent_category: Category | null
  similar: Product[]
}

export interface CategoryPageData {
  category: Category
  subcategories: Category[]
  active_subcategory: string | null
  products: Product[]
}

export interface HomeFeed {
  categories: CategoryTree[]
  sections: { title: string; category_slug: string; products: Product[] }[]
}

export interface Store {
  id: number
  name: string
  slug: string
  address: string
  city: string
  pincode: string
  lat: number
  lng: number
  phone: string | null
  timezone: string
  opens_at: string
  closes_at: string
  pickup_start: string
  pickup_end: string
  supports_delivery: boolean
  supports_pickup: boolean
  supports_instore: boolean
  delivery_radius_km: number
  is_open_now: boolean
  distance_km: number | null
  delivers_here: boolean | null
  eta_minutes: number | null
}

export interface StoreDetail extends Store {
  layout_rows: number
  aisles: { number: number; name: string }[]
}

export interface Serviceability {
  deliverable: boolean
  store: Store | null
  eta_minutes: number | null
  message: string
}

export interface PickupSlot {
  start: string
  end: string
  label: string
  available: boolean
  remaining: number
}

export interface PickupDay {
  date: string
  label: string
  slots: PickupSlot[]
}

export interface Bill {
  item_total: number
  mrp_total: number
  savings: number
  delivery_fee: number
  handling_fee: number
  small_cart_fee: number
  grand_total: number
}

export interface QuoteLine {
  product: Product
  requested_quantity: number
  quantity: number
  line_total: number
  line_mrp_total: number
  issue: string | null
}

export interface Quote {
  store_id: number
  fulfillment_type: FulfillmentType
  lines: QuoteLine[]
  item_count: number
  bill: Bill
  free_delivery_gap: number | null
  notes: string[]
  can_checkout: boolean
  blocking_issues: string[]
  unavailable_product_ids: number[]
}

export interface Address {
  id: number
  label: 'Home' | 'Work' | 'Other'
  receiver_name: string
  receiver_phone: string | null
  house: string
  area: string
  landmark: string | null
  city: string
  pincode: string
  lat: number
  lng: number
  is_default: boolean
}

export type AddressInput = Omit<Address, 'id'>

export interface OrderItem {
  product_id: number
  name: string
  unit_label: string
  emoji: string
  image_url: string | null
  price: number
  mrp: number
  quantity: number
  line_total: number
  location: ShelfLocation | null
}

export interface TimelineStep {
  status: OrderStatus
  label: string
  done: boolean
  current: boolean
  at: string | null
}

export interface PaymentInfo {
  provider: string
  status: PaymentState
  method: string | null
  reference: string | null
  refund_id: string | null
  error: string | null
}

/** What Razorpay Checkout (or the test-payment sheet) needs to take a payment. */
export interface PaymentSession {
  provider: 'razorpay' | 'simulated'
  key_id: string | null
  provider_order_id: string
  amount: number // paise
  currency: string
  order_id: number
  order_code: string
  name: string
  description: string
  prefill: { name: string | null; contact: string; email: string | null }
  expires_at: string | null
}

export interface Order {
  id: number
  code: string
  fulfillment_type: FulfillmentType
  status: OrderStatus
  status_label: string
  payment_method: PaymentMethod
  payment_status: PaymentStatus
  payment_due: boolean
  payment_expires_at: string | null
  payment: PaymentInfo | null
  store: { id: number; name: string; address: string; phone: string | null; lat: number; lng: number }
  delivery_address: { label: string; receiver_name: string; receiver_phone: string | null; line: string } | null
  eta_minutes: number | null
  pickup_slot_start: string | null
  pickup_slot_end: string | null
  handover_pin: string | null
  item_count: number
  item_total: number
  mrp_total: number
  savings: number
  delivery_fee: number
  handling_fee: number
  small_cart_fee: number
  grand_total: number
  notes: string | null
  items: OrderItem[]
  timeline: TimelineStep[]
  can_cancel: boolean
  created_at: string
  customer: { name: string | null; phone: string } | null
}

export interface OrderSummary {
  id: number
  code: string
  fulfillment_type: FulfillmentType
  status: OrderStatus
  status_label: string
  store_name: string
  item_count: number
  grand_total: number
  created_at: string
  pickup_slot_start: string | null
  preview: string[]
}

export interface ResolvedItem {
  query: string
  quantity: number
  product: Product
  in_stock: boolean
  line_total: number
  confidence: number
  step: number
  alternatives: Product[]
}

export interface UnmatchedItem {
  query: string
  quantity: number
  suggestions: Product[]
}

export interface ShoppingList {
  store: Store
  layout_rows: number
  aisle_count: number
  items: ResolvedItem[]
  unmatched: UnmatchedItem[]
  route: { aisle: number; name: string | null; item_count: number }[]
  item_count: number
  total: number
  mrp_total: number
  savings: number
  out_of_stock_count: number
}

export interface CartLine {
  product_id: number
  quantity: number
}
