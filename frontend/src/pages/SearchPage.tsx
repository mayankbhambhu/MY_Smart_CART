import { ArrowLeft, Clock, MapPin, Search, TrendingUp, X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { ProductGrid } from '../components/product'
import { EmptyState, ErrorState, Skeleton } from '../components/ui'
import { shortStoreName } from '../lib/format'
import { useSearch } from '../lib/queries'
import { clearRecentSearches, recentSearches, rememberSearch } from '../lib/recent'
import { useShop } from '../lib/shop'

const TRENDING = ['milk', 'bread', 'eggs', 'atta', 'maggi', 'paneer', 'chips', 'coke', 'doodh', 'ice cream']

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms)
    return () => window.clearTimeout(timer)
  }, [value, ms])
  return debounced
}

export default function SearchPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [text, setText] = useState(params.get('q') ?? '')
  const [recent, setRecent] = useState(recentSearches)
  const query = useDebounced(text.trim(), 250)
  const { storeId, mode, store } = useShop()
  const results = useSearch(query, storeId)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setParams(query ? { q: query } : {}, { replace: true })
  }, [query, setParams])

  const pick = (value: string) => {
    setText(value)
    rememberSearch(value)
    setRecent(recentSearches())
  }

  return (
    <div className="px-4 pt-4">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          pick(text)
          input.current?.blur()
        }}
        className="flex items-center gap-2"
        role="search"
      >
        <button type="button" onClick={() => navigate(-1)} className="grid size-11 shrink-0 place-items-center rounded-xl bg-white shadow-sm ring-1 ring-black/5" aria-label="Go back">
          <ArrowLeft className="size-5" />
        </button>
        <label className="flex h-11 flex-1 items-center gap-2 rounded-xl bg-white px-3.5 shadow-sm ring-1 ring-black/10 focus-within:ring-2 focus-within:ring-brand-600">
          <Search className="size-[18px] text-gray-500" aria-hidden />
          <input
            ref={input}
            autoFocus
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={mode === 'instore' ? 'Which item are you looking for?' : 'Search for atta, dal, coke and more'}
            className="h-full min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-gray-400"
            aria-label="Search products"
            enterKeyHint="search"
          />
          {text && (
            <button type="button" onClick={() => setText('')} className="grid size-6 place-items-center rounded-full bg-gray-200 text-gray-600" aria-label="Clear search">
              <X className="size-3.5" />
            </button>
          )}
        </label>
      </form>

      {mode === 'instore' && store && (
        <p className="mt-3 flex items-center gap-1.5 rounded-xl bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-800">
          <MapPin className="size-4" /> Showing where each item is in {shortStoreName(store.name)}
        </p>
      )}

      {!query ? (
        <div className="mt-6 space-y-6">
          {recent.length > 0 && (
            <section>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-bold">Recent searches</h2>
                <button
                  type="button"
                  className="text-xs font-semibold text-brand-700"
                  onClick={() => {
                    clearRecentSearches()
                    setRecent([])
                  }}
                >
                  Clear
                </button>
              </div>
              <Chips items={recent} icon={<Clock className="size-3.5 text-gray-400" />} onPick={pick} />
            </section>
          )}
          <section>
            <h2 className="mb-2 text-sm font-bold">Trending near you</h2>
            <Chips items={TRENDING} icon={<TrendingUp className="size-3.5 text-brand-600" />} onPick={pick} />
          </section>
          <p className="text-xs text-gray-500">Tip: Hindi names work too — try "doodh", "pyaz" or "cheeni".</p>
        </div>
      ) : results.error ? (
        <ErrorState error={results.error} onRetry={() => results.refetch()} />
      ) : results.isLoading ? (
        <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      ) : results.data?.products.length ? (
        <div className="mt-4">
          <p className="mb-3 text-sm text-gray-500">
            Showing results for <span className="font-semibold text-ink">"{results.data.query}"</span>
          </p>
          <ProductGrid products={results.data.products} />
        </div>
      ) : (
        <EmptyState emoji="🔍" title={`No results for "${query}"`} body="Check the spelling or try a more general word like 'milk' or 'snacks'." />
      )}
    </div>
  )
}

function Chips({ items, icon, onPick }: { items: string[]; icon: ReactNode; onPick: (value: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onPick(item)}
          className="flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-sm font-medium shadow-sm ring-1 ring-black/10 hover:bg-gray-50"
        >
          {icon}
          {item}
        </button>
      ))}
    </div>
  )
}
