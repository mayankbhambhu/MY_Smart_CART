import type {
  Address,
  AddressInput,
  CartItem,
  Category,
  CategoryWithProducts,
  InStoreMatchResponse,
  InStoreRoute,
  Mode,
  Order,
  OrderCreate,
  PickupDay,
  Product,
  Quote,
  StaffOrder,
  Store,
  StoreLayout,
  User,
} from "./types";

const TOKEN_KEY = "smartcart.token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const tokenStore = {
  get: () => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string | null) => {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable (private mode) – stay logged in for this tab only */
    }
  },
};

function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  // FastAPI validation errors: [{ msg: "..." }]
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, "");
  return fallback;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errorMessage(data, `Request failed (${res.status})`));
  return data as T;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export const api = {
  requestOtp: (phone: string) =>
    request<{ message: string; expires_in_seconds: number; dev_otp: string | null }>("POST", "/auth/otp/request", {
      phone,
    }),
  verifyOtp: (phone: string, otp: string) =>
    request<{ access_token: string; user: User }>("POST", "/auth/otp/verify", { phone, otp }),
  me: () => request<User>("GET", "/auth/me"),
  updateMe: (body: Partial<Pick<User, "name" | "email">>) => request<User>("PATCH", "/auth/me", body),

  stores: (lat?: number, lng?: number) => request<Store[]>("GET", `/stores${qs({ lat, lng })}`),
  nearestStore: (lat: number, lng: number) => request<Store>("GET", `/stores/nearest${qs({ lat, lng })}`),
  store: (id: number) => request<StoreLayout>("GET", `/stores/${id}`),
  pickupSlots: (storeId: number) => request<{ days: PickupDay[] }>("GET", `/stores/${storeId}/pickup-slots`),
  matchList: (storeId: number, text: string) =>
    request<InStoreMatchResponse>("POST", `/stores/${storeId}/instore/match`, { text }),
  shoppingRoute: (storeId: number, items: CartItem[]) =>
    request<InStoreRoute>("POST", `/stores/${storeId}/instore/list`, { items }),

  categories: () => request<Category[]>("GET", "/categories"),
  home: (storeId: number) => request<CategoryWithProducts[]>("GET", `/home${qs({ store_id: storeId })}`),
  products: (params: { storeId: number; categoryId?: number; q?: string; limit?: number }) =>
    request<Product[]>(
      "GET",
      `/products${qs({ store_id: params.storeId, category_id: params.categoryId, q: params.q, limit: params.limit })}`,
    ),
  product: (id: number, storeId: number) => request<Product>("GET", `/products/${id}${qs({ store_id: storeId })}`),

  quote: (storeId: number, fulfillment: Mode, items: CartItem[]) =>
    request<Quote>("POST", "/cart/quote", { store_id: storeId, fulfillment, items }),

  addresses: () => request<Address[]>("GET", "/addresses"),
  addAddress: (body: AddressInput) => request<Address>("POST", "/addresses", body),
  deleteAddress: (id: number) => request<void>("DELETE", `/addresses/${id}`),

  placeOrder: (body: OrderCreate) => request<Order>("POST", "/orders", body),
  orders: () => request<Order[]>("GET", "/orders"),
  order: (id: number) => request<Order>("GET", `/orders/${id}`),
  cancelOrder: (id: number) => request<Order>("POST", `/orders/${id}/cancel`),

  staffOrders: (storeId: number, active = true) =>
    request<StaffOrder[]>("GET", `/staff/orders${qs({ store_id: storeId, active })}`),
  advanceOrder: (id: number) => request<StaffOrder>("POST", `/staff/orders/${id}/advance`),
  verifyCode: (storeId: number, code: string) =>
    request<StaffOrder>("POST", "/staff/verify-code", { store_id: storeId, code }),
};
