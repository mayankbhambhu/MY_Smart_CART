import { useMutation, useQueryClient } from '@tanstack/react-query'
import { create } from 'zustand'

import { toast } from '../store/toast'
import { ApiError, api, messageOf } from './api'
import type { Order, PaymentSession } from './types'

// ---- Razorpay Checkout ---------------------------------------------------------------------
// https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/

const CHECKOUT_JS = 'https://checkout.razorpay.com/v1/checkout.js'

interface RazorpaySuccess {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

interface RazorpayFailure {
  error: { code: string; description: string; reason?: string }
}

interface RazorpayOptions {
  key: string
  order_id: string
  amount: number
  currency: string
  name: string
  description: string
  prefill: { name?: string; contact?: string; email?: string }
  notes: Record<string, string>
  theme: { color: string }
  handler: (response: RazorpaySuccess) => void
  modal: { ondismiss: () => void; confirm_close: boolean }
}

interface RazorpayCheckout {
  open: () => void
  on: (event: 'payment.failed', callback: (response: RazorpayFailure) => void) => void
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => RazorpayCheckout
  }
}

let checkoutScript: Promise<void> | null = null

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  checkoutScript ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = CHECKOUT_JS
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      checkoutScript = null // let the next attempt try again
      script.remove()
      reject(new Error("Couldn't load the payment page. Check your connection (or ad blocker) and try again."))
    }
    document.head.appendChild(script)
  })
  return checkoutScript
}

/** The customer closed Checkout without paying. `reason` is set if an attempt failed first. */
export class PaymentCancelled extends Error {
  reason: string | null

  constructor(reason: string | null = null) {
    super(reason ? `Payment failed: ${reason}` : 'Payment cancelled')
    this.name = 'PaymentCancelled'
    this.reason = reason
  }
}

/** Money may have moved, but the server hasn't confirmed it with Razorpay yet. */
export class PaymentConfirming extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PaymentConfirming'
  }
}

async function openRazorpay(session: PaymentSession): Promise<RazorpaySuccess> {
  await loadCheckout()
  const Razorpay = window.Razorpay
  if (!Razorpay || !session.key_id) throw new Error("Couldn't start the payment. Please try again.")
  return new Promise((resolve, reject) => {
    let lastFailure: string | null = null
    const checkout = new Razorpay({
      key: session.key_id!,
      order_id: session.provider_order_id,
      amount: session.amount,
      currency: session.currency,
      name: session.name,
      description: session.description,
      prefill: {
        name: session.prefill.name ?? undefined,
        contact: session.prefill.contact,
        email: session.prefill.email ?? undefined,
      },
      notes: { order_code: session.order_code },
      theme: { color: '#0c831f' },
      handler: resolve,
      // Checkout shows failures itself and lets the customer retry; we only hear back when they leave.
      modal: { ondismiss: () => reject(new PaymentCancelled(lastFailure)), confirm_close: true },
    })
    checkout.on('payment.failed', (response) => {
      lastFailure = response.error.description || 'The payment was declined'
    })
    checkout.open()
  })
}

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

async function confirmRazorpay(orderId: number, response: RazorpaySuccess): Promise<Order> {
  try {
    return await api<Order>(`/payments/orders/${orderId}/razorpay/verify`, { body: response })
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 502) throw error
    // Paid, but Razorpay didn't answer our double-check. Ask again a few times before giving up
    // (the webhook will settle it too).
    for (const delay of [2000, 4000, 8000]) {
      await sleep(delay)
      const order = await api<Order>(`/payments/orders/${orderId}/refresh`, { method: 'POST' }).catch(() => null)
      if (order && !order.payment_due) return order
    }
    throw new PaymentConfirming(error.message)
  }
}

// ---- Test payments (deployments without Razorpay keys) ----------------------------------------

type SimulatedOutcome = 'success' | 'failure' | 'dismissed'

interface TestPaymentState {
  session: PaymentSession | null
  settle: (outcome: SimulatedOutcome) => void
  ask: (session: PaymentSession) => Promise<SimulatedOutcome>
}

/** Drives the test-payment sheet (see components/TestPaymentSheet.tsx). */
export const useTestPayment = create<TestPaymentState>()((set, get) => ({
  session: null,
  settle: () => {},
  ask: (session) => {
    get().settle('dismissed') // only one sheet at a time
    return new Promise((resolve) =>
      set({
        session,
        settle: (outcome) => {
          set({ session: null, settle: () => {} })
          resolve(outcome)
        },
      }),
    )
  },
}))

async function payWithSimulator(orderId: number, session: PaymentSession): Promise<Order> {
  const outcome = await useTestPayment.getState().ask(session)
  if (outcome === 'dismissed') throw new PaymentCancelled()
  const order = await api<Order>(`/payments/orders/${orderId}/simulate`, { body: { outcome } })
  if (outcome === 'failure') throw new PaymentCancelled(order.payment?.error ?? 'The payment was declined')
  return order
}

// ---- Paying for an order -----------------------------------------------------------------------

/** Takes the customer through paying for an order and returns it once the server has the money. */
export async function payForOrder(orderId: number): Promise<Order> {
  const session = await api<PaymentSession>(`/payments/orders/${orderId}/session`, { method: 'POST' })
  if (session.provider === 'simulated') return payWithSimulator(orderId, session)
  const response = await openRazorpay(session)
  return confirmRazorpay(orderId, response)
}

export function usePayOrder() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: payForOrder,
    onSuccess: (order) => {
      client.setQueryData(['order', order.id], order)
      client.invalidateQueries({ queryKey: ['orders'] })
      toast('Payment successful', 'success')
    },
    onError: (error, orderId) => {
      client.invalidateQueries({ queryKey: ['order', orderId] })
      if (error instanceof PaymentCancelled) toast(error.message, error.reason ? 'error' : 'info')
      else toast(messageOf(error), error instanceof PaymentConfirming ? 'info' : 'error')
    },
  })
}

/** Re-checks an unpaid order with the gateway, e.g. the customer paid and closed the tab. */
export function useRefreshPayment() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (orderId: number) => api<Order>(`/payments/orders/${orderId}/refresh`, { method: 'POST' }),
    onSuccess: (order) => {
      client.setQueryData(['order', order.id], order)
      if (!order.payment_due) client.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}
