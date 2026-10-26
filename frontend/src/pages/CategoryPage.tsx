import { useParams, useSearchParams } from 'react-router'

import { ProductGrid } from '../components/product'
import { EmptyState, ErrorState, PageHeader, Skeleton } from '../components/ui'
import { cn } from '../lib/cn'
import { plural } from '../lib/format'
import { useCategoryPage } from '../lib/queries'
import { useShop } from '../lib/shop'

export default function CategoryPage() {
  const { slug = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const sub = params.get('sub')
  const { storeId } = useShop()
  const page = useCategoryPage(slug, sub, storeId)

  if (page.error) return <ErrorState error={page.error} onRetry={() => page.refetch()} />
  const data = page.data
  const active = data?.subcategories.find((s) => s.slug === data.active_subcategory)

  const select = (value: string | null) => {
    setParams(value ? { sub: value } : {}, { replace: true })
    window.scrollTo({ top: 0 })
  }

  return (
    <div>
      <PageHeader
        title={data?.category.name ?? 'Loading…'}
        subtitle={data && `${active ? active.name : 'All items'} · ${plural(data.products.length, 'item')}`}
      />
      <div className="flex items-start">
        <nav
          className="sticky top-[var(--header-h)] max-h-[calc(100dvh-var(--header-h))] w-[84px] shrink-0 overflow-y-auto border-r border-black/5 bg-white pb-24 md:w-56 md:rounded-tr-2xl"
          aria-label="Subcategories"
        >
          <SidebarItem label="All" emoji={data?.category.emoji ?? '🛒'} active={!data?.active_subcategory} onClick={() => select(null)} />
          {data?.subcategories.map((s) => (
            <SidebarItem key={s.id} label={s.name} emoji={s.emoji} active={data.active_subcategory === s.slug} onClick={() => select(s.slug)} />
          ))}
        </nav>
        <div className="min-w-0 flex-1 p-2.5 md:p-4">
          {page.isLoading ? (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="h-64" />
              ))}
            </div>
          ) : data?.products.length ? (
            <ProductGrid products={data.products} />
          ) : (
            <EmptyState emoji="🧺" title="Nothing here yet" body="Check back soon — we're stocking up." />
          )}
        </div>
      </div>
    </div>
  )
}

function SidebarItem({ label, emoji, active, onClick }: { label: string; emoji: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active}
      className={cn(
        'relative flex w-full flex-col items-center gap-1 px-1.5 py-3 text-center md:flex-row md:gap-3 md:px-4 md:text-left',
        active ? 'bg-brand-50/60' : 'hover:bg-gray-50',
      )}
    >
      {active && <span className="absolute inset-y-2 right-0 w-1 rounded-l-full bg-brand-600 md:left-0 md:right-auto md:rounded-l-none md:rounded-r-full" />}
      <span className={cn('grid size-12 shrink-0 place-items-center rounded-full text-2xl', active ? 'bg-white shadow-sm' : 'bg-gray-100')} aria-hidden>
        {emoji}
      </span>
      <span className={cn('text-[11px] leading-tight md:text-sm', active ? 'font-bold text-ink' : 'font-medium text-gray-600')}>{label}</span>
    </button>
  )
}
