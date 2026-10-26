import { MapPin, Minus, Plus, ShoppingBag, Timer } from 'lucide-react'
import { Link } from 'react-router'

import { cn } from '../lib/cn'
import { formatINR } from '../lib/format'
import { useShop } from '../lib/shop'
import type { Product } from '../lib/types'
import { useCart } from '../store/cart'
import { useInStore } from '../store/instore'
import { toast } from '../store/toast'

const IMAGE_SIZES = {
  sm: 'text-3xl',
  md: 'text-[3.4rem]',
  lg: 'text-[7rem] sm:text-[9rem]',
}

export function ProductImage({
  product,
  size = 'md',
  className,
}: {
  product: Pick<Product, 'name' | 'emoji' | 'image_url'>
  size?: keyof typeof IMAGE_SIZES
  className?: string
}) {
  if (product.image_url) {
    return <img src={product.image_url} alt={product.name} loading="lazy" className={cn('object-contain', className)} />
  }
  return (
    <div className={cn('grid select-none place-items-center leading-none', IMAGE_SIZES[size], className)} aria-hidden>
      <span className="drop-shadow-sm">{product.emoji}</span>
    </div>
  )
}

function productPath(product: Pick<Product, 'id' | 'slug'>) {
  return `/p/${product.id}/${product.slug}`
}

/** "ADD" that turns into a − qty + stepper. Adds to the cart, or to the in-store list in in-store mode. */
export function AddButton({ product, size = 'md' }: { product: Product; size?: 'md' | 'lg' }) {
  const { mode, storeId } = useShop()
  const inStore = mode === 'instore'

  const cartQty = useCart((s) => s.lines[product.id]?.qty ?? 0)
  const listQty = useInStore((s) =>
    storeId != null ? (s.lists[storeId]?.find((e) => e.productId === product.id)?.quantity ?? 0) : 0,
  )
  const qty = inStore ? listQty : cartQty
  const outOfStock = product.availability != null && !product.availability.in_stock
  const maxQty = inStore ? 50 : (product.availability?.max_qty ?? 10)

  const increment = () => {
    if (qty >= maxQty) {
      toast(product.availability && maxQty === product.availability.stock ? `Only ${maxQty} left` : `Max ${maxQty} per order`)
      return
    }
    if (inStore) {
      if (storeId == null) return
      useInStore.getState().addEntries(storeId, [{ productId: product.id, query: product.name, quantity: 1 }])
      if (qty === 0) toast(`Added to your list${product.location ? ` · ${product.location.label}` : ''}`, 'success')
    } else {
      useCart.getState().add(product)
    }
  }
  const decrement = () => {
    if (inStore) {
      if (storeId != null) useInStore.getState().setQty(storeId, product.id, qty - 1)
    } else {
      useCart.getState().decrement(product.id)
    }
  }

  const sizing = size === 'lg' ? 'h-11 min-w-[120px] text-base' : 'h-9 min-w-[72px] text-sm'
  if (outOfStock && !inStore) {
    return (
      <span className={cn('inline-grid place-items-center rounded-lg border border-gray-200 px-2 font-semibold text-gray-400', sizing, size === 'md' && 'text-[11px]')}>
        Sold out
      </span>
    )
  }
  if (qty === 0) {
    return (
      <button
        type="button"
        onClick={increment}
        className={cn(
          'rounded-lg border font-extrabold tracking-wide shadow-sm transition active:scale-95',
          inStore
            ? 'border-indigo-600 bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
            : 'border-brand-600 bg-brand-50 text-brand-700 hover:bg-brand-100',
          sizing,
        )}
        aria-label={`Add ${product.name}`}
      >
        ADD
      </button>
    )
  }
  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg font-bold text-white shadow-sm',
        inStore ? 'bg-indigo-600' : 'bg-brand-600',
        sizing,
      )}
    >
      <button type="button" onClick={decrement} className="grid h-full w-8 place-items-center" aria-label={`Remove one ${product.name}`}>
        <Minus className="size-4" strokeWidth={3} />
      </button>
      <span aria-live="polite">{qty}</span>
      <button type="button" onClick={increment} className="grid h-full w-8 place-items-center" aria-label={`Add one more ${product.name}`}>
        <Plus className="size-4" strokeWidth={3} />
      </button>
    </div>
  )
}

/** Small chip under the image: delivery time, pickup, or the shelf location when in store. */
export function ModeTag({ product }: { product: Product }) {
  const { mode, eta } = useShop()
  const base = 'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide'
  if (mode === 'instore') {
    if (!product.location) return <span className={cn(base, 'bg-gray-100 text-gray-500')}>Not in this store</span>
    return (
      <span className={cn(base, 'bg-indigo-50 text-indigo-700')}>
        <MapPin className="size-3" aria-hidden /> {product.location.label}
      </span>
    )
  }
  if (mode === 'pickup') {
    return (
      <span className={cn(base, 'bg-amber-50 text-amber-700')}>
        <ShoppingBag className="size-3" aria-hidden /> Pickup
      </span>
    )
  }
  return (
    <span className={cn(base, 'bg-gray-100 text-gray-600')}>
      <Timer className="size-3" aria-hidden /> {eta ?? 10} mins
    </span>
  )
}

export function Price({ price, mrp, size = 'sm' }: { price: number; mrp: number; size?: 'sm' | 'lg' }) {
  return (
    <div className={cn('leading-tight', size === 'lg' && 'flex items-baseline gap-2')}>
      <p className={cn('font-bold', size === 'lg' ? 'text-2xl' : 'text-[13px]')}>{formatINR(price)}</p>
      {mrp > price && (
        <p className={cn('text-gray-400 line-through', size === 'lg' ? 'text-base' : 'text-[11px]')}>
          {size === 'lg' && 'MRP '}
          {formatINR(mrp)}
        </p>
      )}
    </div>
  )
}

export function ProductCard({ product, className }: { product: Product; className?: string }) {
  const outOfStock = product.availability != null && !product.availability.in_stock
  return (
    <article className={cn('relative flex flex-col rounded-2xl bg-white p-2.5 shadow-sm ring-1 ring-black/5', className)}>
      {product.discount_percent > 0 && (
        <span className="absolute left-3 top-0 z-10 rounded-b-md bg-[#256fef] px-1.5 pb-1 pt-0.5 text-center text-[9px] font-extrabold leading-[1.1] text-white">
          {product.discount_percent}%<br />
          OFF
        </span>
      )}
      <Link to={productPath(product)} className="block" aria-label={product.name}>
        <div className={cn('relative aspect-square overflow-hidden rounded-xl bg-[#f5f6f8]', outOfStock && 'grayscale')}>
          <ProductImage product={product} className="size-full" />
          {outOfStock && (
            <span className="absolute inset-x-2 bottom-2 rounded-md bg-gray-800/80 py-1 text-center text-[10px] font-bold uppercase text-white">
              Out of stock
            </span>
          )}
        </div>
      </Link>
      <div className="mt-2 flex flex-1 flex-col">
        <div>
          <ModeTag product={product} />
        </div>
        <Link to={productPath(product)} className="mt-1.5 line-clamp-2 min-h-[2.5em] text-[13px] font-semibold leading-snug text-ink hover:text-brand-700">
          {product.name}
        </Link>
        <p className="mt-0.5 truncate text-xs text-gray-500">{product.unit_label}</p>
        <div className="mt-auto flex items-end justify-between gap-1 pt-2">
          <Price price={product.price} mrp={product.mrp} />
          <AddButton product={product} />
        </div>
      </div>
    </article>
  )
}

export function ProductRail({ products }: { products: Product[] }) {
  return (
    <div className="no-scrollbar -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} className="w-[148px] shrink-0 snap-start sm:w-[172px]" />
      ))}
    </div>
  )
}

export function ProductGrid({ products }: { products: Product[] }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  )
}
