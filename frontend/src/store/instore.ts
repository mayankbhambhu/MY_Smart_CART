import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/** One line of an in-store shopping list. Locations and prices are always fetched fresh. */
export interface ListEntry {
  productId: number
  query: string
  quantity: number
  picked: boolean
}

interface InStoreState {
  lists: Record<number, ListEntry[]>
  addEntries: (storeId: number, entries: Omit<ListEntry, 'picked'>[]) => void
  setQty: (storeId: number, productId: number, quantity: number) => void
  togglePicked: (storeId: number, productId: number) => void
  swap: (storeId: number, fromProductId: number, toProductId: number) => void
  clear: (storeId: number) => void
}

function update(state: InStoreState, storeId: number, fn: (entries: ListEntry[]) => ListEntry[]) {
  return { lists: { ...state.lists, [storeId]: fn(state.lists[storeId] ?? []) } }
}

export const useInStore = create<InStoreState>()(
  persist(
    (set) => ({
      lists: {},
      addEntries: (storeId, incoming) =>
        set((state) =>
          update(state, storeId, (entries) => {
            const next = [...entries]
            for (const item of incoming) {
              const existing = next.findIndex((e) => e.productId === item.productId)
              if (existing >= 0) {
                next[existing] = { ...next[existing], quantity: next[existing].quantity + item.quantity }
              } else {
                next.push({ ...item, picked: false })
              }
            }
            return next
          }),
        ),
      setQty: (storeId, productId, quantity) =>
        set((state) =>
          update(state, storeId, (entries) =>
            quantity <= 0
              ? entries.filter((e) => e.productId !== productId)
              : entries.map((e) => (e.productId === productId ? { ...e, quantity } : e)),
          ),
        ),
      togglePicked: (storeId, productId) =>
        set((state) =>
          update(state, storeId, (entries) =>
            entries.map((e) => (e.productId === productId ? { ...e, picked: !e.picked } : e)),
          ),
        ),
      swap: (storeId, fromProductId, toProductId) =>
        set((state) =>
          update(state, storeId, (entries) => {
            const from = entries.find((e) => e.productId === fromProductId)
            if (!from) return entries
            const rest = entries.filter((e) => e.productId !== fromProductId && e.productId !== toProductId)
            const merged = entries.find((e) => e.productId === toProductId)
            return [
              ...rest,
              {
                ...from,
                productId: toProductId,
                quantity: from.quantity + (merged?.quantity ?? 0),
                picked: false,
              },
            ]
          }),
        ),
      clear: (storeId) => set((state) => update(state, storeId, () => [])),
    }),
    { name: 'smartcart-instore' },
  ),
)

const EMPTY: ListEntry[] = []

export function useStoreList(storeId: number | null): ListEntry[] {
  return useInStore((s) => (storeId != null ? (s.lists[storeId] ?? EMPTY) : EMPTY))
}
