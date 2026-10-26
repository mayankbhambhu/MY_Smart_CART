import type { Store } from './types'

const wholeRupees = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})
const paise = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatINR(amount: number): string {
  return Number.isInteger(amount) ? wholeRupees.format(amount) : paise.format(amount)
}

const STORE_TZ = 'Asia/Kolkata'

export function formatTime(iso: string, timeZone = STORE_TZ): string {
  return new Date(iso)
    .toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone })
    .replace(/\b(am|pm)\b/i, (suffix) => suffix.toUpperCase())
}

export function formatDay(iso: string, timeZone = STORE_TZ): string {
  const date = new Date(iso)
  const key = (d: Date) => d.toLocaleDateString('en-CA', { timeZone })
  const today = new Date()
  const tomorrow = new Date(Date.now() + 86_400_000)
  if (key(date) === key(today)) return 'Today'
  if (key(date) === key(tomorrow)) return 'Tomorrow'
  return date.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', timeZone })
}

export function formatSlot(start: string, end: string, timeZone = STORE_TZ): string {
  return `${formatDay(start, timeZone)}, ${formatTime(start, timeZone)} – ${formatTime(end, timeZone)}`
}

export function formatDateTime(iso: string, timeZone = STORE_TZ): string {
  return new Date(iso)
    .toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true, timeZone })
    .replace(/\b(am|pm)\b/i, (suffix) => suffix.toUpperCase())
}

/** "07:00:00" -> "7 AM", "23:30:00" -> "11:30 PM" */
export function formatClock(hhmmss: string): string {
  const [h, m] = hhmmss.split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour = h % 12 === 0 ? 12 : h % 12
  return m ? `${hour}:${String(m).padStart(2, '0')} ${suffix}` : `${hour} ${suffix}`
}

export function formatPhone(phone: string): string {
  return phone.length === 10 ? `+91 ${phone.slice(0, 5)} ${phone.slice(5)}` : phone
}

export function shortStoreName(name: string): string {
  return name.replace(/^Smart Cart\s*·\s*/, '')
}

export function plural(count: number, word: string, pluralWord = `${word}s`): string {
  return `${count} ${count === 1 ? word : pluralWord}`
}

export function storeHours(store: Store): string {
  if (store.opens_at === store.closes_at) return 'Open 24 hours'
  return `${formatClock(store.opens_at)} – ${formatClock(store.closes_at)}`
}
