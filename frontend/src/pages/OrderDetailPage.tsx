import { Navigation, Phone, ReceiptText } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { BillDetails, FulfillmentChip, StatusBadge, Timeline } from '../components/order'
import { ProductImage } from '../components/product'
import { Button, Card, EmptyState, ErrorState, PageHeader, Sheet, Spinner } from '../components/ui'
import { ApiError, messageOf } from '../lib/api'
import { cn } from '../lib/cn'
import { formatDateTime, formatDay, formatINR, formatTime, plural } from '../lib/format'
import { useCancelOrder, useOrder } from '../lib/queries'
import type { Order, PaymentMethod } from '../lib/types'
import { toast } from '../store/toast'

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  cod: 'Cash / UPI on delivery',
  pay_at_store: 'Pay at store',
  online: 'Paid online',
}

function useNow(intervalMs: number) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs])
  return now
}

function directionsUrl(order: Order) {
  return `https://www.google.com/maps/dir/?api=1&destination=${order.store.lat},${order.store.lng}`
}

function DeliveryHero({ order }: { order: Order }) {
  const now = useNow(30_000)
  const delivered = order.status === 'delivered'
  const cancelled = order.status === 'cancelled'
  const minutesLeft = order.eta_minutes
    ? Math.max(1, Math.ceil(order.eta_minutes - (now - new Date(order.created_at).getTime()) / 60_000))
    : null
  return (
    <div className={cn('relative overflow-hidden rounded-3xl p-5 text-white shadow-md', cancelled ? 'bg-gray-500' : 'bg-gradient-to-br from-brand-600 to-emerald-500')}>
      <span className="absolute -bottom-2 right-3 text-7xl" aria-hidden>
        {delivered ? '🏠' : cancelled ? '🚫' : '🛵'}
      </span>
      <p className="text-sm font-semibold text-white/80">{order.status_label}</p>
      <p className="mt-1 text-3xl font-extrabold">
        {delivered ? 'Delivered!' : cancelled ? 'Order cancelled' : `Arriving in ${minutesLeft} min`}
      </p>
      {order.delivery_address && (
        <p className="mt-2 max-w-[75%] text-sm text-white/90">
          To {order.delivery_address.label} · {order.delivery_address.line}
        </p>
      )}
    </div>
  )
}

function PickupHero({ order }: { order: Order }) {
  const start = order.pickup_slot_start
  const end = order.pickup_slot_end
  const ready = order.status === 'ready_for_pickup'
  const done = order.status === 'picked_up'
  const cancelled = order.status === 'cancelled'
  const message = ready
    ? 'Your order is packed and waiting at the pickup counter.'
    : done
      ? 'Picked up. Thanks for shopping with us!'
      : cancelled
        ? 'This pickup was cancelled.'
        : "We'll pack your order just before your slot."
  return (
    <div className={cn('rounded-3xl p-5 shadow-md', cancelled ? 'bg-gray-100' : ready ? 'bg-gradient-to-br from-amber-400 to-orange-400' : 'bg-gradient-to-br from-amber-100 to-orange-50')}>
      <p className="text-sm font-bold uppercase tracking-wider text-amber-900/70">Pickup slot</p>
      {start && end && (
        <p className="mt-1 text-2xl font-extrabold">
          {formatDay(start)}, {formatTime(start)} – {formatTime(end)}
        </p>
      )}
      <p className="mt-1 text-sm text-gray-800">{message}</p>
      {!cancelled && !done && order.handover_pin && (
        <div className="mt-4 flex items-center gap-4 rounded-2xl bg-white p-4 shadow-sm">
          <QRCodeSVG value={`SMARTCART:${order.code}:${order.handover_pin}`} size={104} level="M" />
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Pickup PIN</p>
            <p className="font-mono text-4xl font-black tracking-[0.25em]">{order.handover_pin}</p>
            <p className="mt-1 text-xs text-gray-500">Show the QR or tell the PIN at the counter</p>
          </div>
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="font-semibold">{order.store.name}</span>
        <a href={directionsUrl(order)} target="_blank" rel="noreferrer" className="flex items-center gap-1 font-bold text-amber-800 underline-offset-2 hover:underline">
          <Navigation className="size-4" /> Directions
        </a>
        {order.store.phone && (
          <a href={`tel:${order.store.phone}`} className="flex items-center gap-1 font-bold text-amber-800 hover:underline">
            <Phone className="size-4" /> Call store
          </a>
        )}
      </div>
    </div>
  )
}

function InStoreHero({ order }: { order: Order }) {
  const paid = order.status === 'completed'
  const cancelled = order.status === 'cancelled'
  return (
    <div className={cn('rounded-3xl p-5 text-white shadow-md', cancelled ? 'bg-gray-500' : paid ? 'bg-gradient-to-br from-brand-600 to-emerald-500' : 'bg-gradient-to-br from-indigo-600 to-violet-600')}>
      <p className="text-sm font-bold uppercase tracking-wider text-white/80">{paid ? 'Paid · exit pass' : cancelled ? 'Bill cancelled' : 'Your bill'}</p>
      <p className="mt-1 text-3xl font-extrabold">{formatINR(order.grand_total)}</p>
      <p className="text-sm text-white/85">
        {plural(order.item_count, 'item')} · {order.store.name}
      </p>
      {!cancelled && (
        <div className="mt-4 flex items-center gap-4 rounded-2xl bg-white p-4 text-ink">
          <QRCodeSVG value={`SMARTCART:${order.code}`} size={104} level="M" />
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Bill code</p>
            <p className="font-mono text-2xl font-black tracking-wider">{order.code}</p>
            <p className="mt-1 text-xs text-gray-500">
              {paid ? 'Show this at the exit if asked.' : 'Show this at the billing counter. The cashier scans it — no re-scanning items.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

const PLACED_MESSAGES = {
  delivery: '🎉 Order placed! Your groceries are on the way.',
  pickup: '✅ Pickup scheduled! Show your PIN at the store counter.',
  in_store: '🧾 Bill created. Head to the billing counter.',
}

export default function OrderDetailPage() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const order = useOrder(Number(id))
  const cancel = useCancelOrder(Number(id))
  const [confirming, setConfirming] = useState(false)

  if (order.isLoading) return <Spinner />
  if (order.error instanceof ApiError && order.error.status === 401) {
    return (
      <EmptyState
        emoji="🔒"
        title="Log in to view this order"
        action={
          <Link to={`/login?next=/orders/${id}`}>
            <Button>Log in</Button>
          </Link>
        }
      />
    )
  }
  if (order.error instanceof ApiError && order.error.status === 404) {
    return <EmptyState emoji="🧾" title="Order not found" body="It may belong to a different account." />
  }
  if (order.error || !order.data) return <ErrorState error={order.error ?? new Error('Order not found')} onRetry={() => order.refetch()} />
  const o = order.data
  const placedBanner =
    params.get('placed') &&
    (o.fulfillment_type === 'in_store' && o.status === 'completed' ? '✅ Payment done. Enjoy your shopping!' : PLACED_MESSAGES[o.fulfillment_type])

  return (
    <div>
      <PageHeader title={`Order #${o.code}`} subtitle={`Placed ${formatDateTime(o.created_at)}`} right={<StatusBadge status={o.status} label={o.status_label} />} />
      <div className="grid grid-cols-1 gap-4 px-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-4">
          {placedBanner && <p className="animate-pop rounded-2xl bg-brand-50 px-4 py-3 font-semibold text-brand-800 ring-1 ring-brand-100">{placedBanner}</p>}
          {o.fulfillment_type === 'delivery' && <DeliveryHero order={o} />}
          {o.fulfillment_type === 'pickup' && <PickupHero order={o} />}
          {o.fulfillment_type === 'in_store' && <InStoreHero order={o} />}

          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-bold">Order status</h2>
              <FulfillmentChip type={o.fulfillment_type} />
            </div>
            <Timeline steps={o.timeline} />
          </Card>

          <Card>
            <h2 className="mb-1 font-bold">{plural(o.item_count, 'item')}</h2>
            <ul className="divide-y divide-gray-100">
              {o.items.map((item) => (
                <li key={item.product_id} className="flex items-center gap-3 py-3">
                  <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-[#f5f6f8]">
                    <ProductImage product={item} size="sm" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{item.name}</p>
                    <p className="text-xs text-gray-500">
                      {item.unit_label} · {item.quantity} × {formatINR(item.price)}
                      {o.fulfillment_type === 'in_store' && item.location && ` · ${item.location.label}`}
                    </p>
                  </div>
                  <p className="text-sm font-bold">{formatINR(item.line_total)}</p>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="space-y-4 lg:sticky lg:top-[calc(var(--header-h)+16px)] lg:self-start">
          <Card>
            <h2 className="mb-2 flex items-center gap-2 font-bold">
              <ReceiptText className="size-5 text-gray-500" /> Bill summary
            </h2>
            <BillDetails bill={o} fulfillment={o.fulfillment_type} />
          </Card>
          <Card className="space-y-1.5 text-sm">
            <p className="flex justify-between">
              <span className="text-gray-500">Payment</span>
              <span className="font-semibold">{PAYMENT_LABELS[o.payment_method]}</span>
            </p>
            <p className="flex justify-between">
              <span className="text-gray-500">Payment status</span>
              <span className={cn('font-semibold capitalize', o.payment_status === 'paid' ? 'text-brand-700' : 'text-gray-700')}>{o.payment_status}</span>
            </p>
            <p className="flex justify-between gap-4">
              <span className="text-gray-500">Store</span>
              <span className="text-right font-semibold">{o.store.name}</span>
            </p>
          </Card>
          {o.can_cancel && (
            <Button tone="danger" block onClick={() => setConfirming(true)}>
              {o.fulfillment_type === 'in_store' ? 'Cancel this bill' : 'Cancel order'}
            </Button>
          )}
        </div>
      </div>

      <Sheet open={confirming} onClose={() => setConfirming(false)} title="Cancel this order?">
        <p className="text-sm text-gray-600">
          {o.fulfillment_type === 'pickup' ? 'Your pickup slot will be released.' : "We'll stop processing it right away."}
          {o.payment_status === 'paid' && ' Your payment will be refunded.'}
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Button tone="secondary" onClick={() => setConfirming(false)}>
            Keep it
          </Button>
          <Button
            tone="danger"
            loading={cancel.isPending}
            onClick={() =>
              cancel.mutate(undefined, {
                onSuccess: () => {
                  setConfirming(false)
                  toast('Order cancelled', 'success')
                },
                onError: (error) => toast(messageOf(error), 'error'),
              })
            }
          >
            Yes, cancel
          </Button>
        </div>
      </Sheet>
    </div>
  )
}
