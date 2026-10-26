import { FlaskConical } from 'lucide-react'

import { formatINR } from '../lib/format'
import { useTestPayment } from '../lib/payments'
import { Button, Sheet } from './ui'

/** Stands in for Razorpay Checkout on deployments without Razorpay keys. */
export function TestPaymentSheet() {
  const session = useTestPayment((s) => s.session)
  const settle = useTestPayment((s) => s.settle)
  if (!session) return null
  const amount = formatINR(session.amount / 100)
  return (
    <Sheet open onClose={() => settle('dismissed')} title="Test payment">
      <div className="rounded-2xl bg-gradient-to-br from-gray-900 to-gray-700 p-4 text-white">
        <p className="text-xs font-semibold uppercase tracking-wider text-white/60">
          {session.name} · {session.description}
        </p>
        <p className="mt-1 text-3xl font-extrabold">{amount}</p>
        <p className="mt-1 text-xs text-white/70">{session.prefill.contact}</p>
      </div>
      <p className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-200">
        <FlaskConical className="mt-0.5 size-4 shrink-0" aria-hidden />
        This is a demo checkout and no money moves. Add Razorpay keys on the server to take real UPI and card payments.
      </p>
      <div className="mt-4 grid gap-2">
        <Button block className="h-12 text-base" onClick={() => settle('success')}>
          Pay {amount}
        </Button>
        <Button tone="danger" block onClick={() => settle('failure')}>
          Simulate a failed payment
        </Button>
      </div>
    </Sheet>
  )
}
