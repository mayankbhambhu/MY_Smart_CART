import { Bike, Check, CircleX, ShoppingBag, Store } from 'lucide-react'

import { cn } from '../lib/cn'
import { formatINR, formatTime } from '../lib/format'
import type { Bill, FulfillmentType, OrderStatus, TimelineStep } from '../lib/types'

const FULFILLMENT_META: Record<FulfillmentType, { label: string; icon: typeof Bike; tone: string }> = {
  delivery: { label: 'Delivery', icon: Bike, tone: 'bg-brand-50 text-brand-700' },
  pickup: { label: 'Scheduled pickup', icon: ShoppingBag, tone: 'bg-amber-50 text-amber-700' },
  in_store: { label: 'In-store', icon: Store, tone: 'bg-indigo-50 text-indigo-700' },
}

const STATUS_TONES: Partial<Record<OrderStatus, string>> = {
  delivered: 'bg-brand-600 text-white',
  picked_up: 'bg-brand-600 text-white',
  completed: 'bg-brand-600 text-white',
  cancelled: 'bg-red-100 text-red-700',
  ready_for_pickup: 'bg-amber-500 text-white',
  out_for_delivery: 'bg-brand-100 text-brand-800',
  awaiting_payment: 'bg-indigo-100 text-indigo-800',
  payment_pending: 'bg-amber-100 text-amber-800',
}

export function StatusBadge({ status, label }: { status: OrderStatus; label: string }) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold', STATUS_TONES[status] ?? 'bg-gray-100 text-gray-700')}>
      {label}
    </span>
  )
}

export function FulfillmentChip({ type }: { type: FulfillmentType }) {
  const meta = FULFILLMENT_META[type]
  const Icon = meta.icon
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold', meta.tone)}>
      <Icon className="size-3.5" aria-hidden /> {meta.label}
    </span>
  )
}

export function Timeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="relative">
      {steps.map((step, index) => {
        const cancelled = step.status === 'cancelled'
        const last = index === steps.length - 1
        return (
          <li key={step.status} className="relative flex gap-3 pb-5 last:pb-0">
            {!last && (
              <span
                className={cn('absolute left-[11px] top-6 h-[calc(100%-12px)] w-0.5', step.done && steps[index + 1]?.done ? 'bg-brand-500' : 'bg-gray-200')}
                aria-hidden
              />
            )}
            <span
              className={cn(
                'relative z-10 grid size-6 shrink-0 place-items-center rounded-full',
                cancelled ? 'bg-red-500 text-white' : step.done ? 'bg-brand-600 text-white' : 'border-2 border-gray-300 bg-white',
                step.current && !cancelled && 'ring-4 ring-brand-100',
              )}
            >
              {cancelled ? <CircleX className="size-4" /> : step.done && <Check className="size-3.5" strokeWidth={3} />}
            </span>
            <div className="-mt-0.5">
              <p className={cn('text-sm font-semibold', !step.done && 'text-gray-400')}>{step.label}</p>
              {step.at && <p className="text-xs text-gray-500">{formatTime(step.at)}</p>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function Row({ label, value, strike, bold, hint }: { label: string; value: string; strike?: string; bold?: boolean; hint?: string }) {
  return (
    <div className={cn('flex items-start justify-between gap-4 py-1 text-sm', bold && 'pt-2 text-base font-bold')}>
      <span className={cn(!bold && 'text-gray-600')}>
        {label}
        {hint && <span className="block text-xs font-normal text-gray-400">{hint}</span>}
      </span>
      <span className="shrink-0 text-right">
        {strike && <span className="mr-1.5 text-gray-400 line-through">{strike}</span>}
        {value}
      </span>
    </div>
  )
}

export function BillDetails({ bill, fulfillment }: { bill: Bill; fulfillment: FulfillmentType }) {
  return (
    <div>
      <Row label="Items total" value={formatINR(bill.item_total)} strike={bill.mrp_total > bill.item_total ? formatINR(bill.mrp_total) : undefined} />
      {fulfillment === 'delivery' && (
        <Row label="Delivery charge" value={bill.delivery_fee > 0 ? formatINR(bill.delivery_fee) : 'FREE'} />
      )}
      {fulfillment === 'pickup' && <Row label="Delivery charge" value="FREE" hint="You're picking up" />}
      {bill.handling_fee > 0 && <Row label="Handling charge" value={formatINR(bill.handling_fee)} />}
      {bill.small_cart_fee > 0 && <Row label="Small cart charge" value={formatINR(bill.small_cart_fee)} hint="Waived on orders above ₹99" />}
      <div className="my-1 border-t border-dashed border-gray-200" />
      <Row label="Grand total" value={formatINR(bill.grand_total)} bold />
      {bill.savings > 0 && (
        <p className="mt-2 rounded-lg bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700">
          Your total savings: {formatINR(bill.savings)}
        </p>
      )}
    </div>
  )
}
