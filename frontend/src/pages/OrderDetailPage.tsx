import { Navigation, Phone, ReceiptText, Wallet } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { BillDetails, FulfillmentChip, StatusBadge, Timeline } from '../components/order'
import { ProductImage } from '../components/product'
import { Button, Card, EmptyState, ErrorState, PageHeader, Sheet, Spinner } from '../components/ui'
import { ApiError, messageOf } from '../lib/api'
import { cn } from '../lib/cn'
import { formatDateTime, formatDay, formatINR, formatTime, plural } from '../lib/format'
import { usePayOrder, useRefreshPayment } from '../lib/payments'
import { useCancelOrder, useOrder } from '../lib/queries'
import type { Order, PaymentMethod } from '../lib/types'
import { toast } from '../store/toast'

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  cod: 'Cash / UPI on delivery',
  pay_at_store: 'Pay at store',
  online: 'Online',
}

const METHOD_LABELS: Record<string, string> = {
  upi: 'UPI',
  card: 'Card',
  netbanking: 'Netbanking',
  wallet: 'Wallet',
  emi: 'EMI',
  paylater: 'Pay later',
  simulated: 'Test payment',
}

function useNow(intervalMs: number) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs])
  return now
}

function useCountdown(deadline: string | null): number | null {
  const now = useNow(1000)
  return deadline ? Math.max(0, Math.floor((new Date(deadline).getTime() - now) / 1000)) : null
}

const mmss = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`

/** When the order really started: payment time for online orders, else creation time. */
function placedAt(order: Order): string {
  return order.timeline.find((step) => step.status === 'placed')?.at ?? order.created_at
}

function directionsUrl(order: Order) {
  return `https://www.google.com/maps/dir/?api=1&destination=${order.store.lat},${order.store.lng}`
}

function DeliveryHero({ order }: { order: Order }) {
  const now = useNow(30_000)
  const delivered = order.status === 'delivered'
  const cancelled = order.status === 'cancelled'
  const unpaid = order.status === 'payment_pending'
  const minutesLeft = order.eta_minutes
    ? Math.max(1, Math.ceil(order.eta_minutes - Math.max(0, now - new Date(placedAt(order)).getTime()) / 60_000))
    : null
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-3xl p-5 text-white shadow-md',
        cancelled ? 'bg-gray-500' : unpaid ? 'bg-gradient-to-br from-amber-500 to-orange-500' : 'bg-gradient-to-br from-brand-600 to-emerald-500',
      )}
    >
      <span className="absolute -bottom-2 right-3 text-7xl" aria-hidden>
        {delivered ? '🏠' : cancelled ? '🚫' : unpaid ? '💳' : '🛵'}
      </span>
      <p className="text-sm font-semibold text-white/80">{order.status_label}</p>
      <p className="mt-1 text-3xl font-extrabold">
        {delivered
          ? 'Delivered!'
          : cancelled
            ? 'Order cancelled'
            : unpaid
              ? `Pay to get it in ~${order.eta_minutes} min`
              : `Arriving in ${minutesLeft} min`}
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
  const unpaid = order.status === 'payment_pending'
  const message = ready
    ? 'Your order is packed and waiting at the pickup counter.'
    : done
      ? 'Picked up. Thanks for shopping with us!'
      : cancelled
        ? 'This pickup was cancelled.'
        : unpaid
          ? 'Complete the payment to confirm your slot.'
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
      {!cancelled && !done && !unpaid && order.handover_pin && (
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

function PaymentDueCard({ order, paying, onPay }: { order: Order; paying: boolean; onPay: () => void }) {
  const refresh = useRefreshPayment()
  const secondsLeft = useCountdown(order.payment_expires_at)
  const expired = secondsLeft === 0
  const failure = order.payment?.status === 'failed' ? order.payment.error : null
  const inStore = order.fulfillment_type === 'in_store'
  const held = order.fulfillment_type === 'pickup' ? 'your items and pickup slot' : 'your items'

  const checkAgain = () =>
    refresh.mutate(order.id, {
      onSuccess: (latest) =>
        toast(latest.payment_due ? "We haven't received this payment yet" : 'Payment received', latest.payment_due ? 'info' : 'success'),
      onError: (error) => toast(messageOf(error), 'error'),
    })

  return (
    <Card className="ring-2 ring-amber-300">
      <div className="flex items-start gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-700">
          <Wallet className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-bold">{inStore ? 'Pay for your bill in the app' : 'Complete your payment'}</p>
          <p className="text-sm text-gray-600">
            {inStore
              ? 'Or show the bill QR at the counter and pay there.'
              : expired
                ? 'The time to pay is up. Updating your order…'
                : secondsLeft != null && (
                    <>
                      We're holding {held} for <b className="tabular-nums">{mmss(secondsLeft)}</b>
                    </>
                  )}
          </p>
          {failure && <p className="mt-1 text-sm font-semibold text-red-600">Last attempt failed: {failure}</p>}
        </div>
      </div>
      <Button block className="mt-3 h-12 text-base" loading={paying} disabled={expired} onClick={onPay}>
        Pay {formatINR(order.grand_total)}
      </Button>
      {order.payment?.provider === 'razorpay' && (
        <button
          type="button"
          onClick={checkAgain}
          disabled={refresh.isPending}
          className="mt-2 w-full text-center text-sm font-semibold text-gray-600 hover:text-ink"
        >
          {refresh.isPending ? 'Checking…' : 'Already paid? Check again'}
        </button>
      )}
    </Card>
  )
}

function PaymentDetails({ order }: { order: Order }) {
  const payment = order.payment
  const method = payment?.method && payment.status !== 'failed' ? METHOD_LABELS[payment.method] ?? payment.method : null
  return (
    <>
      <p className="flex justify-between">
        <span className="text-gray-500">Payment</span>
        <span className="font-semibold">
          {PAYMENT_LABELS[order.payment_method]}
          {method && order.payment_method === 'online' && ` · ${method}`}
        </span>
      </p>
      <p className="flex justify-between">
        <span className="text-gray-500">Payment status</span>
        <span className={cn('font-semibold capitalize', order.payment_status === 'paid' ? 'text-brand-700' : order.payment_due ? 'text-amber-700' : 'text-gray-700')}>
          {order.payment_due ? 'Waiting for payment' : order.payment_status}
        </span>
      </p>
      {payment?.reference && (
        <p className="flex justify-between gap-4">
          <span className="text-gray-500">Transaction ID</span>
          <span className="truncate font-mono text-xs leading-5">{payment.reference}</span>
        </p>
      )}
      {payment?.status === 'refunded' && (
        <p className="rounded-lg bg-blue-50 px-3 py-2 text-blue-800">
          {payment.provider === 'razorpay'
            ? `Refund of ${formatINR(order.grand_total)} started${payment.refund_id ? ` (${payment.refund_id})` : ''}. It reaches your account in 5–7 working days.`
            : 'Test refund issued. No real money moved.'}
        </p>
      )}
    </>
  )
}

const PLACED_MESSAGES = {
  delivery: '🎉 Order placed! Your groceries are on the way.',
  pickup: '✅ Pickup scheduled! Show your PIN at the store counter.',
  in_store: '🧾 Bill created. Head to the billing counter.',
}

export default function OrderDetailPage() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const order = useOrder(Number(id))
  const cancel = useCancelOrder(Number(id))
  const payOrder = usePayOrder()
  const refreshPayment = useRefreshPayment()
  const [confirming, setConfirming] = useState(false)

  // Arriving from checkout with ?pay=1 opens the payment once. Coming back to an unpaid Razorpay
  // order (paid in another tab or app?) asks the server to check with Razorpay once.
  const data = order.data
  const started = useRef(false)
  useEffect(() => {
    if (!data || started.current) return
    started.current = true
    if (params.get('pay')) {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          next.delete('pay')
          return next
        },
        { replace: true },
      )
      if (data.payment_due) payOrder.mutate(data.id)
    } else if (data.payment_due && data.payment?.provider === 'razorpay') {
      refreshPayment.mutate(data.id)
    }
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

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
    !o.payment_due &&
    o.status !== 'cancelled' &&
    (o.fulfillment_type === 'in_store' && o.status === 'completed' ? '✅ Payment done. Enjoy your shopping!' : PLACED_MESSAGES[o.fulfillment_type])

  return (
    <div>
      <PageHeader title={`Order #${o.code}`} subtitle={`Placed ${formatDateTime(o.created_at)}`} right={<StatusBadge status={o.status} label={o.status_label} />} />
      <div className="grid grid-cols-1 gap-4 px-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-4">
          {placedBanner && <p className="animate-pop rounded-2xl bg-brand-50 px-4 py-3 font-semibold text-brand-800 ring-1 ring-brand-100">{placedBanner}</p>}
          {o.payment_due && <PaymentDueCard order={o} paying={payOrder.isPending} onPay={() => payOrder.mutate(o.id)} />}
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
            <PaymentDetails order={o} />
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
          {o.payment_status === 'paid' && o.payment_method === 'online' && ' Your payment will be refunded.'}
          {o.payment_due && ' Nothing has been charged.'}
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
