import type { ReactNode } from 'react'

import { useActiveStore } from '../lib/queries'
import { ShopContext } from '../lib/shop'

/** Resolves the active store once for the whole app (product cards read it via useShop). */
export function ShopProvider({ children }: { children: ReactNode }) {
  const shop = useActiveStore()
  return <ShopContext.Provider value={shop}>{children}</ShopContext.Provider>
}
