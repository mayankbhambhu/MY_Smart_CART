import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { Product } from '../lib/types'

/** Just enough of a product to draw the cart bar instantly; prices are re-checked by the server. */
export type CartProduct = Pick<Product, 'id' | 'name' | 'unit_label' | 'price' | 'mrp' | 'emoji' | 'image_url'>

interface CartLineState {
  product: CartProduct
  qty: number
}

interface CartState {
  lines: Record<number, CartLineState>
  add: (product: CartProduct) => void
  decrement: (productId: number) => void
  setQty: (productId: number, qty: number) => void
  remove: (productIds: number[]) => void
  clear: () => void
}

const snapshot = (p: CartProduct): CartProduct => ({
  id: p.id,
  name: p.name,
  unit_label: p.unit_label,
  price: p.price,
  mrp: p.mrp,
  emoji: p.emoji,
  image_url: p.image_url,
})

export const useCart = create<CartState>()(
  persist(
    (set) => ({
      lines: {},
      add: (product) =>
        set((state) => {
          const current = state.lines[product.id]
          return {
            lines: { ...state.lines, [product.id]: { product: snapshot(product), qty: (current?.qty ?? 0) + 1 } },
          }
        }),
      decrement: (productId) =>
        set((state) => {
          const current = state.lines[productId]
          if (!current) return state
          const lines = { ...state.lines }
          if (current.qty <= 1) delete lines[productId]
          else lines[productId] = { ...current, qty: current.qty - 1 }
          return { lines }
        }),
      setQty: (productId, qty) =>
        set((state) => {
          const current = state.lines[productId]
          if (!current) return state
          const lines = { ...state.lines }
          if (qty <= 0) delete lines[productId]
          else lines[productId] = { ...current, qty }
          return { lines }
        }),
      remove: (productIds) =>
        set((state) => {
          const lines = { ...state.lines }
          for (const id of productIds) delete lines[id]
          return { lines }
        }),
      clear: () => set({ lines: {} }),
    }),
    { name: 'smartcart-cart' },
  ),
)

export function useCartSummary() {
  const lines = useCart((s) => s.lines)
  const all = Object.values(lines)
  return {
    lines: all,
    count: all.reduce((sum, line) => sum + line.qty, 0),
    total: all.reduce((sum, line) => sum + line.qty * line.product.price, 0),
  }
}
