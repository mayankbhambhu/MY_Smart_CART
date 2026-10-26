import { useMutation } from '@tanstack/react-query'
import { Bike, KeyRound, MapPin, Phone, ScanLine, ShoppingBag, Store } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { StatusBadge } from '../components/order'
import { Button, Card, EmptyState, PageHeader, Segmented, Skeleton } from '../components/ui'
import { messageOf } from '../lib/api'
import { formatDateTime, formatDay, formatINR, formatPhone, formatTime, plural } from '../lib/format'
import { lookupOrder, useStaffAction, useStaffOrders, useStaffStore } from '../lib/queries'
import type { FulfillmentType, Order, OrderStatus } from '../lib/types'
import { isStaff, useAuth } from '../store/auth'
import { toast } from '../store/toast'

type Action = { label: string; status?: OrderStatus; complete?: boolean; tone?: 'primary' | 'danger' | 'amber' | 'indigo' }

/** Next steps the store team can take, mirroring STAFF_TRANSITIONS on the server. */
function actionsFor(order: Order): Action[] {
  const cancel: Action = { label: 'Cancel', status: 'cancelled', tone: 'danger' }
  if (order.fulfillment_type === 'delivery') {
    switch (order.status) {
      case 'placed':
        return [{ label: 'Confirm order', status: 'confirmed' }, cancel]
      case 'confirmed':
        return [{ label: 'Start packing', status: 'packing' }, cancel]
      case 'packing':
        return [{ label: 'Out for delivery', status: 'out_for_delivery' }, cancel]
      case 'out_for_delivery':
        return [{ label: 'Mark delivered', complete: true }]
      default:
        return []
    }
  }
  if (order.fulfillment_type === 'pickup') {
    switch (order.status) {
      case 'placed':
        return [{ label: 'Confirm order', status: 'confirmed', tone: 'amber' }, cancel]
      case 'confirmed':
        return [{ label: 'Start packing', status: 'packing', tone: 'amber' }, cancel]
      case 'packing':
        return [{ label: 'Mark ready for pickup', status: 'ready_for_pickup', tone: 'amber' }, cancel]
      case 'ready_for_pickup':
        return [cancel]
      default:
        return []
    }
  }
  return order.status === 'awaiting_payment' ? [{ label: 'Payment received', complete: true, tone: 'indigo' }, { ...cancel, label: 'Cancel bill' }] : []
}

function OrderCard({ order, onUpdated }: { order: Order; onUpdated?: (order: Order) => void }) {
  const action = useStaffAction()
  const [pin, setPin] = useState('')
  // Picking list in shelf order so packers walk the store once.
  const items = [...order.items].sort((a, b) => (a.location?.aisle ?? 99) - (b.location?.aisle ?? 99) || (a.location?.row ?? 0) - (b.location?.row ?? 0))

  const run = (step: Action | { complete: true; label: string }) =>
    action.mutate(
      { orderId: order.id, status: 'status' in step ? step.status : undefined, complete: step.complete, pin },
      {
        onSuccess: (updated) => {
          toast(`${updated.code}: ${updated.status_label}`, 'success')
          setPin('')
          onUpdated?.(updated)
        },
        onError: (error) => toast(messageOf(error), 'error'),
      },
    )

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-mono text-lg font-black tracking-wide">#{order.code}</p>
          <p className="text-xs text-gray-500">Placed {formatDateTime(order.created_at)}</p>
        </div>
        <StatusBadge status={order.status} label={order.status_label} />
      </div>

      {order.fulfillment_type === 'pickup' && order.pickup_slot_start && order.pickup_slot_end && (
        <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm font-bold text-amber-800">
          Pickup {formatDay(order.pickup_slot_start)}, {formatTime(order.pickup_slot_start)} – {formatTime(order.pickup_slot_end)}
        </p>
      )}
      {order.fulfillment_type === 'delivery' && order.delivery_address && (
        <p className="flex items-start gap-1.5 text-sm text-gray-600">
          <MapPin className="mt-0.5 size-4 shrink-0" /> {order.delivery_address.line}
        </p>
      )}
      {order.customer && (
        <p className="flex items-center gap-1.5 text-sm">
          <Phone className="size-4 text-gray-400" />
          <span className="font-semibold">{order.customer.name ?? 'Customer'}</span>
          <a href={`tel:+91${order.customer.phone}`} className="text-brand-700 hover:underline">
            {formatPhone(order.customer.phone)}
          </a>
        </p>
      )}

      <ul className="divide-y divide-gray-100 rounded-xl border border-gray-100 px-3">
        {items.map((item) => (
          <li key={item.product_id} className="flex items-center gap-2 py-2 text-sm">
            <span className="text-xl">{item.emoji}</span>
            <span className="min-w-0 flex-1 truncate">
              <b>{item.quantity} ×</b> {item.name} <span className="text-gray-400">({item.unit_label})</span>
            </span>
            {item.location && <span className="shrink-0 rounded-md bg-indigo-50 px-1.5 py-0.5 text-[11px] font-bold text-indigo-700">{item.location.label}</span>}
          </li>
        ))}
      </ul>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500">
          {plural(order.item_count, 'item')} · {order.payment_status === 'paid'
            ? 'Paid'
            : order.payment_method === 'cod'
              ? 'Collect on delivery'
              : order.payment_due
                ? 'Paying in the app (or collect at counter)'
                : 'Collect at counter'}
        </span>
        <span className="text-lg font-extrabold">{formatINR(order.grand_total)}</span>
      </div>

      {order.fulfillment_type === 'pickup' && order.status === 'ready_for_pickup' && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            run({ complete: true, label: 'Hand over' })
          }}
          className="flex gap-2"
        >
          <label className="flex h-11 flex-1 items-center gap-2 rounded-xl border border-gray-300 px-3 focus-within:border-amber-500">
            <KeyRound className="size-4 text-gray-400" />
            <input
              inputMode="numeric"
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
              placeholder="Customer's 4-digit PIN"
              className="h-full min-w-0 flex-1 bg-transparent font-mono tracking-widest outline-none"
              aria-label="Pickup PIN"
            />
          </label>
          <Button tone="amber" type="submit" loading={action.isPending} disabled={pin.length !== 4}>
            Hand over
          </Button>
        </form>
      )}

      {actionsFor(order).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {actionsFor(order).map((step) => (
            <Button key={step.label} tone={step.tone ?? 'primary'} className="h-10 flex-1" loading={action.isPending && action.variables?.status === step.status} onClick={() => run(step)}>
              {step.label}
            </Button>
          ))}
        </div>
      )}
    </Card>
  )
}

function Lookup() {
  const [code, setCode] = useState('')
  const [found, setFound] = useState<Order | null>(null)
  const lookup = useMutation({
    mutationFn: (value: string) => lookupOrder(value.replace(/^SMARTCART:/i, '').split(':')[0]),
    onSuccess: setFound,
    onError: (error) => {
      setFound(null)
      toast(messageOf(error), 'error')
    },
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (code.trim()) lookup.mutate(code.trim())
  }
  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex gap-2">
        <label className="flex h-11 flex-1 items-center gap-2 rounded-xl border border-gray-300 bg-white px-3 focus-within:border-brand-600">
          <ScanLine className="size-4 text-gray-400" />
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Order / bill code, e.g. SC7K3M9Q"
            className="h-full min-w-0 flex-1 bg-transparent font-mono uppercase outline-none placeholder:font-sans placeholder:normal-case"
            aria-label="Order code"
          />
        </label>
        <Button type="submit" loading={lookup.isPending}>
          Find
        </Button>
      </form>
      {found && <OrderCard order={found} onUpdated={setFound} />}
    </div>
  )
}

export default function StaffPage() {
  const user = useAuth((s) => s.user)
  const store = useStaffStore()
  const [tab, setTab] = useState<FulfillmentType>('pickup')
  const [activeOnly, setActiveOnly] = useState(true)
  const orders = useStaffOrders(tab, activeOnly)

  if (!isStaff(user)) {
    return (
      <div>
        <PageHeader title="Store dashboard" />
        <EmptyState
          emoji="🏪"
          title="For store staff only"
          body="Log in with a store staff account (demo: 9000000001) to manage pickups, deliveries and in-store bills."
          action={
            <Link to="/login?next=/staff">
              <Button>Log in as staff</Button>
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Store dashboard" subtitle={store.data ? store.data.name : user?.role === 'admin' ? 'All stores (admin)' : ''} />
      <div className="space-y-4 px-4">
        <Card>
          <h2 className="mb-1 font-bold">Scan or enter a code</h2>
          <p className="mb-3 text-sm text-gray-500">Customer's pickup QR / bill QR shows the order code.</p>
          <Lookup />
        </Card>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <Segmented<FulfillmentType>
            value={tab}
            onChange={setTab}
            className="w-full sm:w-auto"
            options={[
              { value: 'pickup', label: <><ShoppingBag className="size-4" /> Pickups</> },
              { value: 'delivery', label: <><Bike className="size-4" /> Deliveries</> },
              { value: 'in_store', label: <><Store className="size-4" /> In-store bills</> },
            ]}
          />
          <label className="flex items-center gap-2 text-sm font-medium">
            <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} className="size-4 accent-brand-600" />
            Active only
          </label>
        </div>

        {orders.isLoading ? (
          <Skeleton className="h-48" />
        ) : orders.data?.length === 0 ? (
          <EmptyState emoji="✅" title="All caught up" body={`No ${activeOnly ? 'active ' : ''}${tab === 'in_store' ? 'in-store bills' : `${tab} orders`} right now.`} />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {orders.data?.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
