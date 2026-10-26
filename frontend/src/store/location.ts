import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/** How the shopper wants their groceries right now. */
export type ShopMode = 'delivery' | 'pickup' | 'instore'

export interface PlaceOption {
  label: string
  lat: number
  lng: number
}

// Demo stores are in Gurugram; these presets make it easy to try different areas.
export const PRESET_PLACES: PlaceOption[] = [
  { label: 'Sector 29, Gurugram', lat: 28.4655, lng: 77.0661 },
  { label: 'DLF Phase 3, Gurugram', lat: 28.4935, lng: 77.0935 },
  { label: 'Sohna Road, Gurugram', lat: 28.4162, lng: 77.0441 },
  { label: 'Connaught Place, New Delhi', lat: 28.6315, lng: 77.2167 },
]

interface LocationState {
  mode: ShopMode
  lat: number
  lng: number
  label: string
  addressId: number | null
  /** Store picked for pickup / in-store. Null means "nearest". */
  storeId: number | null
  setMode: (mode: ShopMode) => void
  setPlace: (place: PlaceOption & { addressId?: number | null }) => void
  setStoreId: (storeId: number | null) => void
}

export const useLocation = create<LocationState>()(
  persist(
    (set) => ({
      mode: 'delivery',
      ...PRESET_PLACES[0],
      addressId: null,
      storeId: null,
      setMode: (mode) => set({ mode }),
      setPlace: ({ label, lat, lng, addressId = null }) => set({ label, lat, lng, addressId }),
      setStoreId: (storeId) => set({ storeId }),
    }),
    { name: 'smartcart-location' },
  ),
)
