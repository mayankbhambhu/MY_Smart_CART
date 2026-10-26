import { Check, Clock, LocateFixed, MapPin, Plus, Store as StoreIcon } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { cn } from '../lib/cn'
import { formatClock, shortStoreName, storeHours } from '../lib/format'
import { useAddresses, useStores } from '../lib/queries'
import { useAuth } from '../store/auth'
import { PRESET_PLACES, useLocation } from '../store/location'
import { toast } from '../store/toast'
import { Sheet } from './ui'

/** Where should we deliver? GPS, a saved address, or one of the demo areas. */
export function LocationSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { label, addressId, setPlace } = useLocation()
  const token = useAuth((s) => s.token)
  const addresses = useAddresses()
  const [locating, setLocating] = useState(false)

  const useGps = () => {
    if (!navigator.geolocation) {
      toast("Your browser can't share location", 'error')
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        setPlace({ label: 'Current location', lat: pos.coords.latitude, lng: pos.coords.longitude })
        onClose()
      },
      () => {
        setLocating(false)
        toast('Could not get your location. Pick an area instead.', 'error')
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    )
  }

  return (
    <Sheet open={open} onClose={onClose} title="Select delivery location">
      <button
        type="button"
        onClick={useGps}
        className="flex w-full items-center gap-3 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3 text-left font-semibold text-brand-700 hover:bg-brand-100"
      >
        <LocateFixed className={cn('size-5', locating && 'animate-pulse')} />
        {locating ? 'Finding you…' : 'Use my current location'}
      </button>

      {token && (
        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">Saved addresses</h3>
            <Link to="/addresses?new=1" onClick={onClose} className="flex items-center gap-1 text-sm font-semibold text-brand-700">
              <Plus className="size-4" /> Add new
            </Link>
          </div>
          {addresses.data?.length === 0 && <p className="text-sm text-gray-500">No saved addresses yet.</p>}
          <ul className="space-y-2">
            {addresses.data?.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  onClick={() => {
                    setPlace({ label: `${a.label} · ${a.area}`, lat: a.lat, lng: a.lng, addressId: a.id })
                    onClose()
                  }}
                  className={cn(
                    'flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left hover:bg-gray-50',
                    addressId === a.id ? 'border-brand-600 bg-brand-50/40' : 'border-gray-200',
                  )}
                >
                  <MapPin className="mt-0.5 size-4 shrink-0 text-gray-500" />
                  <span className="min-w-0">
                    <span className="block font-semibold">{a.label}</span>
                    <span className="block truncate text-sm text-gray-500">
                      {a.house}, {a.area}, {a.city}
                    </span>
                  </span>
                  {addressId === a.id && <Check className="ml-auto size-4 text-brand-600" />}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-500">Popular areas</h3>
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {PRESET_PLACES.map((place) => (
            <li key={place.label}>
              <button
                type="button"
                onClick={() => {
                  setPlace(place)
                  onClose()
                }}
                className={cn(
                  'flex w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm hover:bg-gray-50',
                  label === place.label && addressId == null ? 'border-brand-600 font-semibold' : 'border-gray-200',
                )}
              >
                <MapPin className="size-4 shrink-0 text-gray-400" /> {place.label}
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-gray-500">Smart Cart currently delivers within 5 km of its Gurugram stores.</p>
      </div>
    </Sheet>
  )
}

/** Choose the store for scheduled pickup or in-store shopping. */
export function StoreSheet({
  open,
  onClose,
  purpose,
}: {
  open: boolean
  onClose: () => void
  purpose: 'pickup' | 'instore'
}) {
  const stores = useStores()
  const { storeId, setStoreId } = useLocation()
  const selected = storeId ?? stores.data?.[0]?.id

  return (
    <Sheet open={open} onClose={onClose} title={purpose === 'pickup' ? 'Pick up from' : 'Which store are you in?'}>
      <ul className="space-y-2">
        {stores.data?.map((store, index) => (
          <li key={store.id}>
            <button
              type="button"
              onClick={() => {
                setStoreId(store.id)
                onClose()
              }}
              className={cn(
                'flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left hover:bg-gray-50',
                selected === store.id
                  ? purpose === 'pickup'
                    ? 'border-amber-500 bg-amber-50/50'
                    : 'border-indigo-500 bg-indigo-50/50'
                  : 'border-gray-200',
              )}
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gray-100">
                <StoreIcon className="size-5 text-gray-600" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2 font-semibold">
                  {shortStoreName(store.name)}
                  {index === 0 && store.distance_km != null && (
                    <span className="rounded bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-brand-700">Nearest</span>
                  )}
                </span>
                <span className="block truncate text-sm text-gray-500">{store.address}</span>
                <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                  {store.distance_km != null && <span>{store.distance_km.toFixed(1)} km away</span>}
                  <span className={cn('flex items-center gap-1', store.is_open_now ? 'text-brand-700' : 'text-red-600')}>
                    <Clock className="size-3" />
                    {store.is_open_now ? 'Open now' : 'Closed now'} · {storeHours(store)}
                  </span>
                  {purpose === 'pickup' && (
                    <span>
                      Pickup {formatClock(store.pickup_start)} – {formatClock(store.pickup_end)}
                    </span>
                  )}
                </span>
              </span>
              {selected === store.id && <Check className="mt-1 size-4 shrink-0 text-gray-700" />}
            </button>
          </li>
        ))}
      </ul>
    </Sheet>
  )
}
