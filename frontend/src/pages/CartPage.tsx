import { Bike, CalendarClock, ChevronRight, Clock, MapPin, Minus, Plus, ShoppingBag, Store as StoreIcon, Wallet } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { StoreSheet } from '../components/LocationSheets'
import { BillDetails } from '../components/order'
import { ProductImage } from '../components/product'
import { Button, Card, EmptyState, PageHeader, Segmented, Sheet, Skeleton } from '../components/ui'
import { messageOf } from '../lib/api'
import { cn } from '../lib/cn'
import { formatINR, formatSlot, plural, shortStoreName } from '../lib/format'
import { useAddresses, usePickupSlots, usePlaceOrder, useQuote } from '../lib/queries'
import { useShop } from '../lib/shop'
import type { Address, PaymentMethod, PickupDay, QuoteLine } from '../lib/types'
import { useAuth } from '../store/auth'
import { useCart, useCartSummary, type CartProduct } from '../store/cart'
import { useLocation } from '../store/location'
import { toast } from '../store/toast'

type Fulfillment = 'delivery' | 'pickup'

const PAYMENT_OPTIONS: Record<Fulfillment, { value: PaymentMethod; label: string; hint: string }[]> = {
  delivery: [
    { value: 'cod', label: 'Cash / UPI on delivery', hint: 'Pay the delivery partner' },
    { value: 'online', label: 'Pay online now', hint: 'UPI / card (demo, no real charge)' },
  ],
  pickup: [
    { value: 'pay_at_store', label: 'Pay at the store', hint: 'Pay when you collect' },
    { value: 'online', label: 'Pay online now', hint: 'UPI / card (demo, no real charge)' },
  ],
}

function LineRow({ product, qty, line }: { product: CartProduct; qty: number; line?: QuoteLine }) {
  const { setQty, add, decrement } = useCart.getState()
  const issue = line?.issue
  const max = line?.product.availability?.max_qty
  return (
    <li className="flex items-center gap-3 py-3">
      <Link to={`/p/${product.id}`} className="grid size-16 shrink-0 place-items-center rounded-xl bg-[#f5f6f8]">
        <ProductImage product={product} size="sm" className="text-4xl" />
      </Link>
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-semibold leading-snug">{product.name}</p>
        <p className="text-xs text-gray-500">{product.unit_label}</p>
        {issue ? (
          <p className="mt-1 text-xs font-semibold text-red-600">
            {issue}
            {line && line.quantity > 0 && line.quantity < qty && (
              <button type="button" onClick={() => setQty(product.id, line.quantity)} className="ml-2 underline">
                Update to {line.quantity}
              </button>
            )}
            {line && line.quantity === 0 && (
              <button type="button" onClick={() => setQty(product.id, 0)} className="ml-2 underline">
                Remove
              </button>
            )}
          </p>
        ) : (
          <p className="mt-0.5 text-sm font-bold">
            {formatINR((line?.product.price ?? product.price) * qty)}
            {(line?.product.mrp ?? product.mrp) > (line?.product.price ?? product.price) && (
              <span className="ml-1.5 text-xs font-normal text-gray-400 line-through">
                {formatINR((line?.product.mrp ?? product.mrp) * qty)}
              </span>
            )}
          </p>
        )}
      </div>
      <div className="flex h-9 w-[84px] shrink-0 items-center justify-between rounded-lg bg-brand-600 font-bold text-white">
        <button type="button" onClick={() => decrement(product.id)} className="grid h-full w-8 place-items-center" aria-label={`Remove one ${product.name}`}>
          <Minus className="size-4" strokeWidth={3} />
        </button>
        <span>{qty}</span>
        <button
          type="button"
          onClick={() => (max != null && qty >= max ? toast(`Only ${max} available`) : add(product))}
          className="grid h-full w-8 place-items-center"
          aria-label={`Add one more ${product.name}`}
        >
          <Plus className="size-4" strokeWidth={3} />
        </button>
      </div>
    </li>
  )
}

function AddressSheet({ open, onClose, addresses }: { open: boolean; onClose: () => void; addresses: Address[] }) {
  const { addressId, setPlace } = useLocation()
  return (
    <Sheet open={open} onClose={onClose} title="Deliver to">
      <ul className="space-y-2">
        {addresses.map((a) => (
          <li key={a.id}>
            <button
              type="button"
              onClick={() => {
                setPlace({ label: `${a.label} · ${a.area}`, lat: a.lat, lng: a.lng, addressId: a.id })
                onClose()
              }}
              className={cn('w-full rounded-xl border px-4 py-3 text-left hover:bg-gray-50', addressId === a.id ? 'border-brand-600 bg-brand-50/40' : 'border-gray-200')}
            >
              <p className="font-semibold">{a.label}</p>
              <p className="text-sm text-gray-500">
                {a.house}, {a.area}, {a.city} {a.pincode}
              </p>
            </button>
          </li>
        ))}
      </ul>
      <Link to="/addresses?new=1&next=/cart" className="mt-4 flex items-center justify-center gap-1 rounded-xl border border-dashed border-brand-600 py-3 font-semibold text-brand-700">
        <Plus className="size-4" /> Add a new address
      </Link>
    </Sheet>
  )
}

function SlotPicker({ days, value, onChange }: { days: PickupDay[]; value: string | null; onChange: (start: string) => void }) {
  const firstOpenDay = Math.max(0, days.findIndex((d) => d.slots.some((s) => s.available)))
  const [dayIndex, setDayIndex] = useState(firstOpenDay)
  const day = days[dayIndex]
  return (
    <div>
      <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {days.map((d, index) => {
          const open = d.slots.filter((s) => s.available).length
          return (
            <button
              key={d.date}
              type="button"
              onClick={() => setDayIndex(index)}
              className={cn(
                'shrink-0 rounded-xl border px-4 py-2 text-left',
                index === dayIndex ? 'border-amber-500 bg-amber-50' : 'border-gray-200 bg-white hover:bg-gray-50',
              )}
            >
              <span className="block text-sm font-bold">{d.label}</span>
              <span className={cn('block text-xs', open ? 'text-gray-500' : 'text-red-500')}>{open ? `${open} slots` : 'No slots'}</span>
            </button>
          )
        })}
      </div>
      {day && day.slots.length === 0 ? (
        <p className="mt-3 rounded-xl bg-gray-50 p-3 text-sm text-gray-500">No pickup slots left for {day.label.toLowerCase()}. Try the next day.</p>
      ) : (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {day?.slots.map((slot) => (
            <button
              key={slot.start}
              type="button"
              disabled={!slot.available}
              onClick={() => onChange(slot.start)}
              className={cn(
                'relative rounded-xl border px-2 py-2.5 text-center text-[13px] font-semibold transition',
                value === slot.start
                  ? 'border-amber-500 bg-amber-500 text-white'
                  : slot.available
                    ? 'border-gray-200 bg-white hover:border-amber-400'
                    : 'border-gray-100 bg-gray-50 text-gray-300 line-through',
              )}
            >
              {slot.label}
              {slot.available && slot.remaining <= 2 && value !== slot.start && (
                <span className="absolute -right-1 -top-2 rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white">{slot.remaining} left</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function CartPage() {
  const navigate = useNavigate()
  const token = useAuth((s) => s.token)
  const { mode, storeId, store, eta, deliverable, isLoading } = useShop()
  const { setMode, addressId, setPlace } = useLocation()
  const cart = useCartSummary()
  const fulfillment: Fulfillment = mode === 'pickup' ? 'pickup' : 'delivery'

  const items = useMemo(() => cart.lines.map((l) => ({ product_id: l.product.id, quantity: l.qty })), [cart.lines])
  const quote = useQuote(storeId, fulfillment, items)
  const addresses = useAddresses()
  const slots = usePickupSlots(fulfillment === 'pickup' ? storeId : null)
  const place = usePlaceOrder()

  // A slot only counts for the store it was picked at; payment choice is remembered per mode.
  const [slot, setSlot] = useState<{ storeId: number | null; start: string } | null>(null)
  const slotStart = slot && slot.storeId === storeId ? slot.start : null
  const [payments, setPayments] = useState<Record<Fulfillment, PaymentMethod>>({ delivery: 'cod', pickup: 'pay_at_store' })
  const payment = payments[fulfillment]
  const setPayment = (method: PaymentMethod) => setPayments((current) => ({ ...current, [fulfillment]: method }))
  const [addressSheet, setAddressSheet] = useState(false)
  const [storeSheet, setStoreSheet] = useState(false)

  // Products removed from the catalog can't be bought; drop them from the cart.
  const unavailable = quote.data?.unavailable_product_ids
  useEffect(() => {
    if (unavailable?.length) {
      useCart.getState().remove(unavailable)
      toast('Some items are no longer sold and were removed', 'info')
    }
  }, [unavailable])

  // Deliver to a saved address: default to the user's default address.
  const selectedAddress = addresses.data?.find((a) => a.id === addressId) ?? null
  useEffect(() => {
    if (fulfillment !== 'delivery' || selectedAddress || !addresses.data?.length) return
    const fallback = addresses.data.find((a) => a.is_default) ?? addresses.data[0]
    setPlace({ label: `${fallback.label} · ${fallback.area}`, lat: fallback.lat, lng: fallback.lng, addressId: fallback.id })
  }, [fulfillment, selectedAddress, addresses.data, setPlace])

  if (cart.count === 0) {
    return (
      <div>
        <PageHeader title="My cart" />
        <EmptyState
          emoji="🛒"
          title="Your cart is empty"
          body="Add fresh groceries, snacks and essentials. Get them delivered in minutes or pick them up."
          action={
            <Link to="/">
              <Button>Start shopping</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const linesById = new Map(quote.data?.lines.map((l) => [l.product.id, l]))
  const slotInfo = slots.data?.flatMap((d) => d.slots).find((s) => s.start === slotStart)

  let blocker: string | null = null
  if (fulfillment === 'delivery' && storeId == null && !isLoading) blocker = "We don't deliver here yet. Try pickup."
  else if (fulfillment === 'pickup' && storeId == null && !isLoading) blocker = 'Choose a pickup store'
  else if (!quote.data) blocker = 'Calculating your bill…'
  else if (!quote.data.can_checkout) blocker = quote.data.blocking_issues[0]
  else if (fulfillment === 'delivery' && token && !selectedAddress) blocker = 'Add a delivery address'
  else if (fulfillment === 'pickup' && !slotStart) blocker = 'Choose a pickup slot'

  const placeOrder = () => {
    if (!token) {
      navigate('/login?next=/cart')
      return
    }
    if (!quote.data || storeId == null || blocker) return
    place.mutate(
      {
        store_id: storeId,
        fulfillment_type: fulfillment,
        items,
        payment_method: payment,
        address_id: fulfillment === 'delivery' ? selectedAddress?.id : null,
        pickup_slot_start: fulfillment === 'pickup' ? slotStart : null,
      },
      {
        onSuccess: (order) => {
          useCart.getState().clear()
          navigate(`/orders/${order.id}?placed=1`, { replace: true })
        },
        onError: (error) => {
          toast(messageOf(error), 'error')
          quote.refetch()
          slots.refetch()
        },
      },
    )
  }

  const total = quote.data?.bill.grand_total
  const cta = (
    <div className="flex items-center gap-3">
      <div className="min-w-[96px]">
        <p className="text-lg font-extrabold leading-tight">{total != null ? formatINR(total) : '—'}</p>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Total</p>
      </div>
      <Button
        tone={fulfillment === 'pickup' ? 'amber' : 'primary'}
        block
        className="h-12 text-base"
        loading={place.isPending}
        disabled={!!token && !!blocker}
        onClick={placeOrder}
      >
        {!token ? 'Login to continue' : (blocker ?? (fulfillment === 'pickup' ? 'Schedule pickup' : 'Place order'))}
        {!blocker && <ChevronRight className="size-5" />}
      </Button>
    </div>
  )

  return (
    <div className="pb-28 lg:pb-0">
      <PageHeader title="Checkout" subtitle={plural(cart.count, 'item')} />
      <div className="grid grid-cols-1 gap-4 px-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-4">
          <Card>
            <Segmented<Fulfillment>
              value={fulfillment}
              onChange={(value) => setMode(value)}
              options={[
                { value: 'delivery', label: <><Bike className="size-4" /> Delivery</> },
                { value: 'pickup', label: <><ShoppingBag className="size-4" /> Pickup</> },
              ]}
            />
            {mode === 'instore' && (
              <p className="mt-3 text-sm text-gray-500">You're in in-store mode. Choose how you'd like to get this cart.</p>
            )}
            {fulfillment === 'delivery' ? (
              <div className="mt-4 flex items-center gap-3">
                <span className="grid size-11 place-items-center rounded-xl bg-brand-50 text-brand-700">
                  <Clock className="size-5" />
                </span>
                <div>
                  <p className="font-bold">{deliverable ? `Delivery in ${eta} minutes` : 'Not delivering to this location'}</p>
                  <p className="text-sm text-gray-500">
                    {store ? `From ${shortStoreName(store.name)} · ` : ''}Shipment of {plural(cart.count, 'item')}
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-4 flex items-center gap-3">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-700">
                  <StoreIcon className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold">{store ? store.name : 'Choose a store'}</p>
                  <p className="truncate text-sm text-gray-500">{store?.address}</p>
                </div>
                <button type="button" onClick={() => setStoreSheet(true)} className="shrink-0 text-sm font-bold text-amber-700">
                  Change
                </button>
              </div>
            )}
          </Card>

          {fulfillment === 'pickup' && (
            <Card>
              <h2 className="mb-3 flex items-center gap-2 font-bold">
                <CalendarClock className="size-5 text-amber-600" /> When will you pick it up?
              </h2>
              {slots.isLoading ? (
                <Skeleton className="h-28" />
              ) : slots.data?.length ? (
                <SlotPicker key={storeId} days={slots.data} value={slotStart} onChange={(start) => setSlot({ storeId, start })} />
              ) : (
                <p className="text-sm text-gray-500">This store isn't taking pickup orders right now.</p>
              )}
              {slotInfo && (
                <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">
                  Pickup {formatSlot(slotInfo.start, slotInfo.end)} · we'll have it packed and ready
                </p>
              )}
            </Card>
          )}

          <Card>
            <h2 className="font-bold">Items</h2>
            <ul className="divide-y divide-gray-100">
              {cart.lines.map(({ product, qty }) => (
                <LineRow key={product.id} product={product} qty={qty} line={linesById.get(product.id)} />
              ))}
            </ul>
          </Card>

          {fulfillment === 'delivery' && (
            <Card>
              <div className="flex items-start gap-3">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-gray-100">
                  <MapPin className="size-5 text-gray-700" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-bold">Delivering to {selectedAddress?.label ?? '…'}</p>
                  {!token ? (
                    <p className="text-sm text-gray-500">Log in to choose a saved address.</p>
                  ) : selectedAddress ? (
                    <p className="text-sm text-gray-500">
                      {selectedAddress.house}, {selectedAddress.area}, {selectedAddress.city}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">You have no saved addresses yet.</p>
                  )}
                </div>
                {token &&
                  (addresses.data?.length ? (
                    <button type="button" onClick={() => setAddressSheet(true)} className="shrink-0 text-sm font-bold text-brand-700">
                      Change
                    </button>
                  ) : (
                    <Link to="/addresses?new=1&next=/cart" className="shrink-0 text-sm font-bold text-brand-700">
                      Add
                    </Link>
                  ))}
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-4 lg:sticky lg:top-[calc(var(--header-h)+16px)] lg:self-start">
          {fulfillment === 'delivery' && quote.data?.free_delivery_gap != null && (
            <div className="rounded-2xl bg-brand-50 p-4 ring-1 ring-brand-100">
              <p className="text-sm font-semibold text-brand-800">
                Add {formatINR(quote.data.free_delivery_gap)} more for FREE delivery
              </p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
                <div
                  className="h-full rounded-full bg-brand-600 transition-all"
                  style={{ width: `${Math.min(100, (quote.data.bill.item_total / (quote.data.bill.item_total + quote.data.free_delivery_gap)) * 100)}%` }}
                />
              </div>
            </div>
          )}
          {quote.data?.notes
            .filter((note) => !note.includes('FREE delivery'))
            .map((note) => (
              <p key={note} className="rounded-xl bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700">
                {note}
              </p>
            ))}

          <Card>
            <h2 className="mb-2 font-bold">Bill details</h2>
            {quote.data ? <BillDetails bill={quote.data.bill} fulfillment={fulfillment} /> : <Skeleton className="h-32" />}
          </Card>

          <Card>
            <h2 className="mb-3 flex items-center gap-2 font-bold">
              <Wallet className="size-5 text-gray-600" /> Payment
            </h2>
            <div className="space-y-2">
              {PAYMENT_OPTIONS[fulfillment].map((option) => (
                <label
                  key={option.value}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5',
                    payment === option.value ? 'border-brand-600 bg-brand-50/50' : 'border-gray-200 hover:bg-gray-50',
                  )}
                >
                  <input
                    type="radio"
                    name="payment"
                    value={option.value}
                    checked={payment === option.value}
                    onChange={() => setPayment(option.value)}
                    className="size-4 accent-brand-600"
                  />
                  <span>
                    <span className="block text-sm font-semibold">{option.label}</span>
                    <span className="block text-xs text-gray-500">{option.hint}</span>
                  </span>
                </label>
              ))}
            </div>
          </Card>

          <div className="hidden lg:block">{cta}</div>
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-black/5 bg-white p-3 pb-[calc(env(safe-area-inset-bottom)+12px)] shadow-[0_-4px_16px_rgba(0,0,0,0.06)] lg:hidden">
        {cta}
      </div>

      <AddressSheet open={addressSheet} onClose={() => setAddressSheet(false)} addresses={addresses.data ?? []} />
      <StoreSheet open={storeSheet} onClose={() => setStoreSheet(false)} purpose="pickup" />
    </div>
  )
}
