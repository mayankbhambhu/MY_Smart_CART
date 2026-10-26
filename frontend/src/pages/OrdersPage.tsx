import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'

import { FulfillmentChip, StatusBadge } from '../components/order'
import { Button, EmptyState, ErrorState, PageHeader, Spinner } from '../components/ui'
import { formatDateTime, formatDay, formatINR, formatTime, plural } from '../lib/format'
import { useOrders } from '../lib/queries'
import { useAuth } from '../store/auth'

export default function OrdersPage() {
  const token = useAuth((s) => s.token)
  const orders = useOrders()

  if (!token) {
    return (
      <div>
        <PageHeader title="My orders" />
        <EmptyState
          emoji="🧾"
          title="Log in to see your orders"
          body="Track deliveries, pickup slots and in-store bills in one place."
          action={
            <Link to="/login?next=/orders">
              <Button>Log in</Button>
            </Link>
          }
        />
      </div>
    )
  }
  if (orders.isLoading) return <Spinner />
  if (orders.error) return <ErrorState error={orders.error} onRetry={() => orders.refetch()} />

  return (
    <div>
      <PageHeader title="My orders" />
      {orders.data?.length === 0 ? (
        <EmptyState
          emoji="🛍️"
          title="No orders yet"
          body="Your deliveries, scheduled pickups and in-store bills will show up here."
          action={
            <Link to="/">
              <Button>Start shopping</Button>
            </Link>
          }
        />
      ) : (
        <ul className="space-y-3 px-4">
          {orders.data?.map((order) => (
            <li key={order.id}>
              <Link to={`/orders/${order.id}`} className="block rounded-2xl bg-white p-4 shadow-sm ring-1 ring-black/5 hover:ring-black/10">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={order.status} label={order.status_label} />
                      <FulfillmentChip type={order.fulfillment_type} />
                    </div>
                    <p className="mt-2 truncate text-sm font-semibold">{order.store_name}</p>
                    <p className="text-xs text-gray-500">
                      {order.pickup_slot_start
                        ? `Pickup ${formatDay(order.pickup_slot_start)}, ${formatTime(order.pickup_slot_start)}`
                        : formatDateTime(order.created_at)}{' '}
                      · #{order.code}
                    </p>
                  </div>
                  <ChevronRight className="mt-1 size-5 shrink-0 text-gray-400" />
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <span className="flex -space-x-2 text-xl">
                    {order.preview.map((emoji, i) => (
                      <span key={i} className="grid size-9 place-items-center rounded-full bg-[#f5f6f8] ring-2 ring-white">
                        {emoji}
                      </span>
                    ))}
                  </span>
                  <span className="text-right text-sm">
                    <span className="block font-bold">{formatINR(order.grand_total)}</span>
                    <span className="block text-xs text-gray-500">{plural(order.item_count, 'item')}</span>
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
