import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '../store/auth'
import { useLocation } from '../store/location'
import { api } from './api'
import type {
  Address,
  AddressInput,
  CartLine,
  CategoryPageData,
  CategoryTree,
  FulfillmentType,
  HomeFeed,
  Order,
  OrderStatus,
  OrderSummary,
  PaymentMethod,
  PickupDay,
  ProductDetail,
  Product,
  Quote,
  Serviceability,
  ShoppingList,
  Store,
  StoreDetail,
  User,
} from './types'

const MINUTE = 60_000

// ---- catalog ---------------------------------------------------------------------------

export const useCategories = () =>
  useQuery({
    queryKey: ['categories'],
    queryFn: () => api<CategoryTree[]>('/categories'),
    staleTime: 10 * MINUTE,
  })

export const useHomeFeed = (storeId: number | null) =>
  useQuery({
    queryKey: ['home', storeId],
    queryFn: () => api<HomeFeed>('/home', { params: { store_id: storeId } }),
    placeholderData: keepPreviousData,
  })

export const useCategoryPage = (slug: string, sub: string | null, storeId: number | null) =>
  useQuery({
    queryKey: ['category', slug, sub, storeId],
    queryFn: () => api<CategoryPageData>(`/categories/${slug}`, { params: { sub, store_id: storeId } }),
    placeholderData: keepPreviousData,
  })

export const useProduct = (id: number, storeId: number | null) =>
  useQuery({
    queryKey: ['product', id, storeId],
    queryFn: () => api<ProductDetail>(`/products/${id}`, { params: { store_id: storeId } }),
    enabled: Number.isFinite(id),
  })

export const useSearch = (q: string, storeId: number | null) =>
  useQuery({
    queryKey: ['search', q, storeId],
    queryFn: ({ signal }) =>
      api<{ query: string; products: Product[] }>('/search', { params: { q, store_id: storeId }, signal }),
    enabled: q.trim().length > 0,
    placeholderData: keepPreviousData,
  })

// ---- stores ----------------------------------------------------------------------------

export const useStores = () => {
  const { lat, lng } = useLocation()
  return useQuery({
    queryKey: ['stores', lat, lng],
    queryFn: () => api<Store[]>('/stores', { params: { lat, lng } }),
    staleTime: MINUTE,
  })
}

export const useServiceability = () => {
  const { lat, lng } = useLocation()
  return useQuery({
    queryKey: ['serviceability', lat, lng],
    queryFn: () => api<Serviceability>('/stores/serviceability', { params: { lat, lng } }),
    staleTime: MINUTE,
  })
}

export const useStoreDetail = (storeId: number | null) =>
  useQuery({
    queryKey: ['store', storeId],
    queryFn: () => api<StoreDetail>(`/stores/${storeId}`),
    enabled: storeId != null,
    staleTime: 10 * MINUTE,
  })

export const usePickupSlots = (storeId: number | null) =>
  useQuery({
    queryKey: ['pickup-slots', storeId],
    queryFn: () => api<PickupDay[]>(`/stores/${storeId}/pickup-slots`),
    enabled: storeId != null,
    refetchInterval: MINUTE,
  })

/**
 * The store that serves the shopper right now: the nearest store that delivers to their
 * location in delivery mode, or the store they picked (default: nearest) for pickup / in-store.
 */
export function useActiveStore() {
  const mode = useLocation((s) => s.mode)
  const chosenId = useLocation((s) => s.storeId)
  const service = useServiceability()
  const stores = useStores()

  if (mode === 'delivery') {
    return {
      mode,
      store: service.data?.store ?? null,
      storeId: service.data?.store?.id ?? null,
      deliverable: service.data?.deliverable ?? false,
      eta: service.data?.eta_minutes ?? null,
      isLoading: service.isLoading,
    }
  }
  const store = stores.data?.find((s) => s.id === chosenId) ?? stores.data?.[0] ?? null
  return {
    mode,
    store,
    storeId: store?.id ?? null,
    deliverable: service.data?.deliverable ?? false,
    eta: service.data?.eta_minutes ?? null,
    isLoading: stores.isLoading,
  }
}

// ---- cart & orders -----------------------------------------------------------------------

export const useQuote = (storeId: number | null, fulfillment: FulfillmentType, items: CartLine[]) =>
  useQuery({
    queryKey: ['quote', storeId, fulfillment, items],
    queryFn: () =>
      api<Quote>('/cart/quote', { body: { store_id: storeId, fulfillment_type: fulfillment, items } }),
    enabled: storeId != null && items.length > 0,
    placeholderData: keepPreviousData,
  })

export interface PlaceOrderInput {
  store_id: number
  fulfillment_type: 'delivery' | 'pickup'
  items: CartLine[]
  payment_method: PaymentMethod
  address_id?: number | null
  pickup_slot_start?: string | null
  notes?: string | null
}

export const usePlaceOrder = () => {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: PlaceOrderInput) => api<Order>('/orders', { body: input }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['orders'] })
      client.invalidateQueries({ queryKey: ['pickup-slots'] })
    },
  })
}

const isFinal = (status: OrderStatus) => ['delivered', 'picked_up', 'completed', 'cancelled'].includes(status)

export const useOrders = () => {
  const token = useAuth((s) => s.token)
  return useQuery({
    queryKey: ['orders'],
    queryFn: () => api<OrderSummary[]>('/orders'),
    enabled: !!token,
  })
}

export const useOrder = (id: number) =>
  useQuery({
    queryKey: ['order', id],
    queryFn: () => api<Order>(`/orders/${id}`),
    // Live tracking: poll until the order is finished (or can't be loaded).
    refetchInterval: (query) =>
      query.state.error || (query.state.data && isFinal(query.state.data.status)) ? false : 8000,
  })

export const useCancelOrder = (id: number) => {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<Order>(`/orders/${id}/cancel`, { method: 'POST' }),
    onSuccess: (order) => {
      client.setQueryData(['order', id], order)
      client.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

// ---- in-store --------------------------------------------------------------------------

export interface ResolveInput {
  text?: string
  items?: { query: string; quantity: number; product_id?: number | null }[]
}

export const resolveShoppingList = (storeId: number, input: ResolveInput) =>
  api<ShoppingList>(`/instore/${storeId}/resolve`, { body: input })

export const useInStoreCheckout = (storeId: number | null) => {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { items: CartLine[]; payment_method: 'pay_at_store' | 'online' }) =>
      api<Order>(`/instore/${storeId}/checkout`, { body: input }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['orders'] }),
  })
}

// ---- account -----------------------------------------------------------------------------

export const useAddresses = () => {
  const token = useAuth((s) => s.token)
  return useQuery({ queryKey: ['addresses'], queryFn: () => api<Address[]>('/addresses'), enabled: !!token })
}

export const useSaveAddress = () => {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...input }: AddressInput & { id?: number }) =>
      id ? api<Address>(`/addresses/${id}`, { method: 'PUT', body: input }) : api<Address>('/addresses', { body: input }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['addresses'] }),
  })
}

export const useDeleteAddress = () => {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api<void>(`/addresses/${id}`, { method: 'DELETE' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['addresses'] }),
  })
}

export const useUpdateProfile = () => {
  const setUser = useAuth((s) => s.setUser)
  return useMutation({
    mutationFn: (input: { name?: string; email?: string }) => api<User>('/auth/me', { method: 'PATCH', body: input }),
    onSuccess: setUser,
  })
}

// ---- staff -------------------------------------------------------------------------------

export const useStaffStore = () =>
  useQuery({ queryKey: ['staff', 'store'], queryFn: () => api<Store | null>('/staff/store') })

export const useStaffOrders = (fulfillment: FulfillmentType, activeOnly: boolean) =>
  useQuery({
    queryKey: ['staff', 'orders', fulfillment, activeOnly],
    queryFn: () =>
      api<Order[]>('/staff/orders', { params: { fulfillment_type: fulfillment, active_only: activeOnly } }),
    refetchInterval: 10_000,
  })

export const useStaffAction = () => {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (action: { orderId: number; status?: OrderStatus; complete?: boolean; pin?: string }) =>
      action.complete
        ? api<Order>(`/staff/orders/${action.orderId}/complete`, { body: { pin: action.pin ?? null } })
        : api<Order>(`/staff/orders/${action.orderId}/status`, { body: { status: action.status } }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['staff'] }),
  })
}

export const lookupOrder = (code: string) => api<Order>('/staff/orders/lookup', { params: { code } })
