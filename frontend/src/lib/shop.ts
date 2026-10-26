import { createContext, useContext } from 'react'

import type { useActiveStore } from './queries'

export type Shop = ReturnType<typeof useActiveStore>

export const ShopContext = createContext<Shop | null>(null)

/** The active mode + store, resolved once by <ShopProvider>. */
export function useShop(): Shop {
  const shop = useContext(ShopContext)
  if (!shop) throw new Error('useShop must be used inside <ShopProvider>')
  return shop
}
