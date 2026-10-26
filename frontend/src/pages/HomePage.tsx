import { ArrowRight, MapPin, Mic, ShoppingBag } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { ProductRail } from '../components/product'
import { ErrorState, Skeleton } from '../components/ui'
import { cn } from '../lib/cn'
import { shortStoreName } from '../lib/format'
import { useHomeFeed } from '../lib/queries'
import { useShop } from '../lib/shop'
import type { CategoryTree } from '../lib/types'
import { useLocation } from '../store/location'
import { toast } from '../store/toast'

function Banners() {
  const navigate = useNavigate()
  const setMode = useLocation((s) => s.setMode)
  const banners = [
    {
      key: 'pickup',
      title: 'Schedule a pickup',
      body: 'No delivery fee. Choose a time slot, we pack your order, you collect it.',
      cta: 'Try pickup',
      emoji: '🛍️',
      className: 'from-amber-200 via-amber-100 to-orange-50',
      onClick: () => {
        setMode('pickup')
        toast('Pickup mode is on. Add items, then pick a slot at checkout.', 'success')
      },
    },
    {
      key: 'instore',
      title: 'Shopping in the store?',
      body: "Tell us your list. We'll show every item's aisle & row, and your total.",
      cta: 'Start my list',
      emoji: '🗺️',
      className: 'from-indigo-200 via-indigo-100 to-violet-50',
      onClick: () => {
        setMode('instore')
        navigate('/instore')
      },
    },
    {
      key: 'delivery',
      title: 'Groceries in minutes',
      body: 'Free delivery on orders above ₹199. Fresh fruits, dairy, snacks & more.',
      cta: 'Shop now',
      emoji: '🛵',
      className: 'from-brand-200 via-brand-100 to-emerald-50',
      onClick: () => {
        setMode('delivery')
        document.getElementById('categories')?.scrollIntoView({ behavior: 'smooth' })
      },
    },
  ]
  return (
    <div className="no-scrollbar -mx-4 flex snap-x gap-3 overflow-x-auto px-4 lg:mx-0 lg:overflow-visible lg:px-0">
      {banners.map((banner) => (
        <div
          key={banner.key}
          className={cn(
            'relative flex w-[86%] shrink-0 snap-start flex-col justify-between overflow-hidden rounded-3xl bg-gradient-to-br p-5 sm:w-[400px] lg:w-auto lg:flex-1 lg:shrink',
            banner.className,
          )}
        >
          <span className="pointer-events-none absolute -bottom-3 -right-2 text-[88px] leading-none opacity-90" aria-hidden>
            {banner.emoji}
          </span>
          <div className="relative max-w-[70%]">
            <h2 className="text-lg font-extrabold leading-tight">{banner.title}</h2>
            <p className="mt-1 text-sm text-gray-700">{banner.body}</p>
          </div>
          <button
            type="button"
            onClick={banner.onClick}
            className="relative mt-4 inline-flex w-fit items-center gap-1 rounded-full bg-ink px-4 py-2 text-sm font-bold text-white hover:bg-black"
          >
            {banner.cta} <ArrowRight className="size-4" />
          </button>
        </div>
      ))}
    </div>
  )
}

/** In-store mode: jump straight into "what do you want to buy?". */
function InStoreQuickStart() {
  const { store } = useShop()
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const submit = (event: FormEvent) => {
    event.preventDefault()
    navigate(text.trim() ? `/instore?q=${encodeURIComponent(text.trim())}` : '/instore')
  }
  return (
    <form onSubmit={submit} className="rounded-3xl bg-gradient-to-br from-indigo-600 to-violet-600 p-5 text-white shadow-lg">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-100">
        <MapPin className="size-4" /> {store ? shortStoreName(store.name) : 'Your store'}
      </p>
      <h2 className="mt-1 text-xl font-extrabold">What do you want to buy?</h2>
      <p className="text-sm text-indigo-100">We'll show the aisle & row of each item and your total.</p>
      <div className="mt-4 flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="2 milk, bread, 6 eggs, maggi"
          className="h-12 min-w-0 flex-1 rounded-xl bg-white px-4 text-ink placeholder:text-gray-400 focus:outline-none"
          aria-label="Shopping list"
        />
        <Link to="/instore?voice=1" className="grid size-12 shrink-0 place-items-center rounded-xl bg-white/15 hover:bg-white/25" aria-label="Speak your list">
          <Mic className="size-5" />
        </Link>
        <button type="submit" className="h-12 shrink-0 rounded-xl bg-white px-4 font-bold text-indigo-700 hover:bg-indigo-50">
          Find
        </button>
      </div>
    </form>
  )
}

function NotServiceable() {
  const setMode = useLocation((s) => s.setMode)
  const label = useLocation((s) => s.label)
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <p className="font-bold">We don't deliver to {label} yet 😔</p>
      <p className="mt-1 text-sm text-gray-600">Change your location from the top, or pick up from a nearby store instead.</p>
      <div className="mt-3 flex gap-2">
        <button type="button" onClick={() => setMode('pickup')} className="flex items-center gap-1.5 rounded-full bg-amber-500 px-3 py-1.5 text-sm font-bold text-white">
          <ShoppingBag className="size-4" /> Schedule pickup
        </button>
        <button type="button" onClick={() => setMode('instore')} className="flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-sm font-bold ring-1 ring-black/10">
          <MapPin className="size-4" /> Shop in store
        </button>
      </div>
    </div>
  )
}

export function CategoryTiles({ categories }: { categories: CategoryTree[] }) {
  return (
    <ul className="grid grid-cols-4 gap-x-2.5 gap-y-4 sm:grid-cols-6 lg:grid-cols-8">
      {categories.map((category) => (
        <li key={category.id}>
          <Link to={`/c/${category.slug}`} className="group flex flex-col items-center gap-1.5 text-center">
            <span
              className="grid aspect-square w-full place-items-center rounded-2xl text-4xl transition group-hover:scale-[1.03] sm:text-5xl"
              style={{ backgroundColor: category.color }}
              aria-hidden
            >
              {category.emoji}
            </span>
            <span className="line-clamp-2 text-[11px] font-semibold leading-tight sm:text-xs">{category.name}</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default function HomePage() {
  const { storeId, mode, deliverable, isLoading: storeLoading } = useShop()
  const feed = useHomeFeed(storeId)

  return (
    <div className="space-y-7 px-4 pt-4">
      {mode === 'delivery' && !storeLoading && !deliverable && <NotServiceable />}
      {mode === 'instore' && <InStoreQuickStart />}
      <Banners />

      <section id="categories" className="scroll-mt-48">
        <h2 className="mb-3 text-lg font-extrabold">Shop by category</h2>
        {feed.isLoading ? (
          <div className="grid grid-cols-4 gap-3 sm:grid-cols-6 lg:grid-cols-8">
            {Array.from({ length: 8 }, (_, i) => (
              <Skeleton key={i} className="aspect-square" />
            ))}
          </div>
        ) : feed.error ? (
          <ErrorState error={feed.error} onRetry={() => feed.refetch()} />
        ) : (
          <CategoryTiles categories={feed.data?.categories ?? []} />
        )}
      </section>

      {feed.data?.sections.map((section) => (
        <section key={section.category_slug}>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-lg font-extrabold">{section.title}</h2>
            <Link to={`/c/${section.category_slug}`} className="text-sm font-bold text-brand-700 hover:underline">
              see all
            </Link>
          </div>
          <ProductRail products={section.products} />
        </section>
      ))}
    </div>
  )
}
