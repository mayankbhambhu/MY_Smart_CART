import {
  Bike,
  ChevronDown,
  ChevronRight,
  House,
  LayoutGrid,
  MapPin,
  ReceiptText,
  Search,
  ShoppingBag,
  ShoppingCart,
  Store,
  UserRound,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, ScrollRestoration, useLocation as useRoute, useNavigate } from 'react-router'

import { cn } from '../lib/cn'
import { formatINR, plural, shortStoreName } from '../lib/format'
import { useAppConfig } from '../lib/queries'
import { useShop } from '../lib/shop'
import { useAuth } from '../store/auth'
import { useCartSummary } from '../store/cart'
import { useStoreList } from '../store/instore'
import { useLocation, type ShopMode } from '../store/location'
import { LocationSheet, StoreSheet } from './LocationSheets'
import { ProductImage } from './product'
import { ShopProvider } from './ShopContext'
import { TestPaymentSheet } from './TestPaymentSheet'
import { Toaster } from './Toaster'

const MODE_THEME: Record<ShopMode, { header: string; accent: string; label: string }> = {
  delivery: { header: 'bg-gradient-to-b from-sun-100 to-white', accent: 'text-brand-700', label: 'Delivery' },
  pickup: { header: 'bg-gradient-to-b from-amber-100 to-white', accent: 'text-amber-700', label: 'Pickup' },
  instore: { header: 'bg-gradient-to-b from-indigo-100 to-white', accent: 'text-indigo-700', label: 'In-store' },
}

export function Logo({ compact }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <img src="/favicon.svg" alt="" className="size-9" />
      {!compact && (
        <span className="text-[22px] font-black tracking-tight">
          <span className="text-brand-700">smart</span>
          <span className="text-[#e8a800]">cart</span>
        </span>
      )}
    </span>
  )
}

export function ModeSwitcher({ className }: { className?: string }) {
  const { mode, setMode } = useLocation()
  const options: { value: ShopMode; label: string; icon: typeof Bike; active: string }[] = [
    { value: 'delivery', label: 'Delivery', icon: Bike, active: 'text-brand-700' },
    { value: 'pickup', label: 'Pickup', icon: ShoppingBag, active: 'text-amber-700' },
    { value: 'instore', label: 'In-store', icon: Store, active: 'text-indigo-700' },
  ]
  return (
    <div className={cn('flex rounded-full bg-black/[0.06] p-1', className)} role="tablist" aria-label="How do you want to shop?">
      {options.map(({ value, label, icon: Icon, active }) => (
        <button
          key={value}
          type="button"
          role="tab"
          aria-selected={mode === value}
          onClick={() => setMode(value)}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] font-bold transition',
            mode === value ? cn('bg-white shadow-sm', active) : 'text-gray-600 hover:text-ink',
          )}
        >
          <Icon className="size-4" aria-hidden />
          {label}
        </button>
      ))}
    </div>
  )
}

function LocationButton() {
  const { mode, store, eta, deliverable, isLoading } = useShop()
  const label = useLocation((s) => s.label)
  const [open, setOpen] = useState(false)

  let title: string
  let subtitle: string
  if (mode === 'delivery') {
    title = isLoading ? 'Finding stores…' : deliverable ? `Delivery in ${eta} minutes` : 'Not delivering here yet'
    subtitle = label
  } else if (mode === 'pickup') {
    title = store ? `Pickup · ${shortStoreName(store.name)}` : 'Choose a pickup store'
    subtitle = store?.distance_km != null ? `${store.distance_km.toFixed(1)} km away · No delivery fee` : 'No delivery fee'
  } else {
    title = store ? `In store · ${shortStoreName(store.name)}` : 'Choose your store'
    subtitle = "Find any item's aisle & row"
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="min-w-0 flex-1 text-left md:w-80 md:flex-none">
        <span className="block truncate text-[19px] font-extrabold leading-tight tracking-tight">{title}</span>
        <span className="mt-0.5 flex items-center gap-1 text-[13px] text-gray-600">
          <span className="truncate">{subtitle}</span>
          <ChevronDown className="size-4 shrink-0" aria-hidden />
        </span>
      </button>
      {mode === 'delivery' ? (
        <LocationSheet open={open} onClose={() => setOpen(false)} />
      ) : (
        <StoreSheet open={open} onClose={() => setOpen(false)} purpose={mode} />
      )}
    </>
  )
}

const SEARCH_HINTS = ['milk', 'atta', 'bread', 'eggs', 'maggi', 'chips', 'paneer', 'coke', 'doodh', 'detergent']

export function SearchLauncher({ className }: { className?: string }) {
  const navigate = useNavigate()
  const { mode } = useShop()
  const [hint, setHint] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setHint((h) => (h + 1) % SEARCH_HINTS.length), 2200)
    return () => window.clearInterval(timer)
  }, [])
  return (
    <button
      type="button"
      onClick={() => navigate('/search')}
      className={cn(
        'flex h-11 w-full items-center gap-2.5 rounded-xl border border-gray-200 bg-white px-3.5 text-left text-sm text-gray-500 shadow-sm hover:border-gray-300',
        className,
      )}
    >
      <Search className="size-[18px] text-gray-700" aria-hidden />
      <span className="truncate">
        {mode === 'instore' ? 'Find in store ' : 'Search '}
        <span key={hint} className="inline-block animate-slide-up">
          "{SEARCH_HINTS[hint]}"
        </span>
      </span>
    </button>
  )
}

function AccountButton() {
  const user = useAuth((s) => s.user)
  if (!user) {
    return (
      <Link to="/login" className="shrink-0 rounded-xl px-3 py-2 text-sm font-bold text-ink hover:bg-black/5">
        Login
      </Link>
    )
  }
  return (
    <Link
      to="/account"
      className="grid size-10 shrink-0 place-items-center rounded-full bg-white text-sm font-bold shadow-sm ring-1 ring-black/10"
      aria-label="Your account"
    >
      {user.name ? user.name.charAt(0).toUpperCase() : <UserRound className="size-5" />}
    </Link>
  )
}

function DesktopCartButton() {
  const { mode, storeId } = useShop()
  const cart = useCartSummary()
  const list = useStoreList(storeId)
  if (mode === 'instore') {
    return (
      <Link to="/instore" className="hidden h-12 shrink-0 items-center gap-2 rounded-xl bg-indigo-600 px-4 font-bold text-white hover:bg-indigo-700 md:flex">
        <MapPin className="size-5" /> My list{list.length > 0 && ` (${list.length})`}
      </Link>
    )
  }
  return (
    <Link to="/cart" className="hidden h-12 shrink-0 items-center gap-2 rounded-xl bg-brand-600 px-4 font-bold text-white hover:bg-brand-700 md:flex">
      <ShoppingCart className="size-5" />
      {cart.count > 0 ? (
        <span className="text-left text-xs leading-tight">
          {plural(cart.count, 'item')}
          <br />
          <span className="text-sm">{formatINR(cart.total)}</span>
        </span>
      ) : (
        'My Cart'
      )}
    </Link>
  )
}

function Header() {
  const { mode } = useShop()
  const route = useRoute()
  const ref = useRef<HTMLElement>(null)
  const showMobileSearch = route.pathname === '/' || route.pathname === '/categories' || route.pathname.startsWith('/c/')

  // Expose the header height so sticky sidebars can sit right below it.
  useEffect(() => {
    const element = ref.current
    if (!element) return
    const update = () => document.documentElement.style.setProperty('--header-h', `${element.offsetHeight}px`)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <header ref={ref} className={cn('sticky top-0 z-40 border-b border-black/5', MODE_THEME[mode].header)}>
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 pb-2 pt-3 md:gap-5 md:py-3">
        <Link to="/" className="hidden shrink-0 md:block" aria-label="Smart Cart home">
          <Logo />
        </Link>
        <LocationButton />
        <div className="hidden flex-1 md:block">
          <SearchLauncher />
        </div>
        <AccountButton />
        <DesktopCartButton />
      </div>
      <div className="mx-auto max-w-6xl px-4 pb-2.5">
        <ModeSwitcher className="md:max-w-md" />
      </div>
      {showMobileSearch && (
        <div className="px-4 pb-3 md:hidden">
          <SearchLauncher />
        </div>
      )}
    </header>
  )
}

const HIDE_CART_BAR = ['/cart', '/login', '/instore', '/staff', '/orders/']

function CartBar() {
  const { mode, storeId } = useShop()
  const route = useRoute()
  const cart = useCartSummary()
  const list = useStoreList(storeId)
  if (HIDE_CART_BAR.some((p) => route.pathname.startsWith(p))) return null

  if (mode === 'instore') {
    if (list.length === 0) return null
    const left = list.filter((e) => !e.picked).length
    return (
      <Link
        to="/instore"
        style={{ bottom: 'calc(var(--nav-h, 0px) + 10px)' }}
        className="fixed inset-x-3 z-30 flex animate-slide-up items-center justify-between rounded-2xl bg-indigo-600 px-4 py-3 text-white shadow-xl md:hidden"
      >
        <span className="flex items-center gap-3">
          <MapPin className="size-5" />
          <span className="text-sm font-bold leading-tight">
            {plural(list.length, 'item')} on your list
            <span className="block text-xs font-medium text-indigo-100">{left} still to pick</span>
          </span>
        </span>
        <span className="flex items-center gap-1 text-sm font-bold">
          Open list <ChevronRight className="size-4" />
        </span>
      </Link>
    )
  }

  if (cart.count === 0) return null
  return (
    <Link
      to="/cart"
      style={{ bottom: 'calc(var(--nav-h, 0px) + 10px)' }}
      className="fixed inset-x-3 z-30 flex animate-slide-up items-center justify-between rounded-2xl bg-brand-600 px-4 py-2.5 text-white shadow-xl md:hidden"
    >
      <span className="flex items-center gap-3">
        <span className="flex -space-x-3">
          {cart.lines.slice(0, 3).map(({ product }) => (
            <span key={product.id} className="grid size-9 place-items-center rounded-full bg-white ring-2 ring-brand-600">
              <ProductImage product={product} size="sm" className="text-xl" />
            </span>
          ))}
        </span>
        <span className="text-sm font-bold leading-tight">
          {plural(cart.count, 'item')}
          <span className="block">{formatINR(cart.total)}</span>
        </span>
      </span>
      <span className="flex items-center gap-1 text-sm font-bold">
        {mode === 'pickup' ? 'Schedule pickup' : 'View cart'} <ChevronRight className="size-4" />
      </span>
    </Link>
  )
}

const HIDE_NAV = ['/cart', '/login', '/staff']

function BottomNav() {
  const route = useRoute()
  const hidden = HIDE_NAV.some((p) => route.pathname.startsWith(p))
  const ref = useRef<HTMLElement>(null)

  // Fixed bars (cart bar, in-store footer) sit on top of the nav using --nav-h.
  useEffect(() => {
    const setHeight = (px: number) => document.documentElement.style.setProperty('--nav-h', `${px}px`)
    const element = ref.current
    if (!element) {
      setHeight(0)
      return
    }
    const update = () => setHeight(element.offsetHeight)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(element)
    return () => {
      observer.disconnect()
      setHeight(0)
    }
  }, [hidden])

  if (hidden) return null
  const items = [
    { to: '/', label: 'Home', icon: House, end: true },
    { to: '/categories', label: 'Categories', icon: LayoutGrid, end: false },
    { to: '/instore', label: 'In-store', icon: Store, end: false },
    { to: '/orders', label: 'Orders', icon: ReceiptText, end: false },
    { to: '/account', label: 'Account', icon: UserRound, end: false },
  ]
  return (
    <nav ref={ref} className="fixed inset-x-0 bottom-0 z-40 border-t border-black/5 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
      <ul className="grid grid-cols-5">
        {items.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center gap-0.5 py-2 text-[11px] font-semibold',
                  isActive ? (to === '/instore' ? 'text-indigo-700' : 'text-brand-700') : 'text-gray-500',
                )
              }
            >
              <Icon className="size-[22px]" aria-hidden />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

/** Tells testers what isn't real on this deployment. */
function DemoBanner() {
  const config = useAppConfig().data
  if (!config) return null
  const notes: string[] = []
  if (config.otp_delivery === 'screen') notes.push('login codes show on screen')
  if (config.payments.provider === 'simulated') notes.push('payments are simulated, no real money moves')
  else if (config.payments.test_mode) notes.push('Razorpay test mode, no real money moves')
  if (notes.length === 0) return null
  return <p className="bg-ink px-4 py-1.5 text-center text-xs font-medium text-white">Demo · {notes.join(' · ')}</p>
}

export function AppShell() {
  return (
    <ShopProvider>
      <div className="min-h-dvh">
        <DemoBanner />
        <Header />
        <main className="mx-auto max-w-6xl pb-40 md:pb-16">
          <Outlet />
        </main>
        <CartBar />
        <BottomNav />
        <Toaster />
        <TestPaymentSheet />
      </div>
      <ScrollRestoration />
    </ShopProvider>
  )
}
