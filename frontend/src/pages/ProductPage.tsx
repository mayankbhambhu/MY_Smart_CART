import { BadgeCheck, MapPin, ShoppingBag, Timer } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { AddButton, Price, ProductImage, ProductRail } from '../components/product'
import { StoreMap } from '../components/StoreMap'
import { Card, ErrorState, PageHeader, Spinner } from '../components/ui'
import { cn } from '../lib/cn'
import { shortStoreName } from '../lib/format'
import { useProduct, useStoreDetail } from '../lib/queries'
import { useShop } from '../lib/shop'
import type { ProductDetail } from '../lib/types'

function InStoreLocation({ product }: { product: ProductDetail }) {
  const { storeId, store } = useShop()
  const layout = useStoreDetail(storeId)
  const location = product.location
  if (!location) {
    return (
      <Card className="border-l-4 border-gray-300">
        <p className="font-semibold">Not sold at {store ? shortStoreName(store.name) : 'this store'}</p>
        <p className="text-sm text-gray-500">Try another store from the top of the screen, or order it for delivery.</p>
      </Card>
    )
  }
  const inStock = product.availability?.in_stock
  return (
    <Card className="overflow-hidden p-0">
      <div className="bg-gradient-to-r from-indigo-600 to-violet-600 p-4 text-white">
        <p className="text-xs font-bold uppercase tracking-wider text-indigo-100">Find it in {store ? shortStoreName(store.name) : 'store'}</p>
        <p className="mt-1 flex items-center gap-2 text-2xl font-extrabold">
          <MapPin className="size-6" /> Aisle {location.aisle} · Row {location.row}
        </p>
        <p className="text-sm text-indigo-100">{location.aisle_name} section</p>
      </div>
      <div className="p-3">
        {layout.data && (
          <StoreMap
            aisles={layout.data.aisles}
            rows={layout.data.layout_rows}
            pins={[{ key: product.id, aisle: location.aisle, row: location.row, status: 'focus', title: product.name }]}
            showRoute={false}
          />
        )}
        <p className={cn('mt-2 text-sm font-semibold', inStock ? 'text-brand-700' : 'text-red-600')}>
          {inStock ? `In stock on the shelf (${product.availability?.stock} left)` : 'Shelf is empty right now — ask a store associate'}
        </p>
      </div>
    </Card>
  )
}

function FulfillmentInfo({ product }: { product: ProductDetail }) {
  const { mode, eta, store } = useShop()
  if (mode === 'instore') return <InStoreLocation product={product} />
  if (mode === 'pickup') {
    return (
      <Card className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-amber-100 text-amber-700">
          <ShoppingBag className="size-5" />
        </span>
        <div>
          <p className="font-semibold">Pick up from {store ? shortStoreName(store.name) : 'your store'}</p>
          <p className="text-sm text-gray-500">Choose a time slot at checkout · no delivery fee</p>
        </div>
      </Card>
    )
  }
  return (
    <Card className="flex items-center gap-3">
      <span className="grid size-11 place-items-center rounded-xl bg-brand-50 text-brand-700">
        <Timer className="size-5" />
      </span>
      <div>
        <p className="font-semibold">Delivery in {eta ?? 10} minutes</p>
        <p className="text-sm text-gray-500">Free delivery on orders above ₹199</p>
      </div>
    </Card>
  )
}

export default function ProductPage() {
  const { id } = useParams()
  const { storeId } = useShop()
  const product = useProduct(Number(id), storeId)

  if (product.isLoading) return <Spinner />
  if (product.error || !product.data) return <ErrorState error={product.error ?? new Error('Product not found')} />
  const p = product.data
  const aliases = p.tags.filter((t) => !p.name.toLowerCase().includes(t.toLowerCase())).slice(0, 5)

  return (
    <div>
      <PageHeader
        title={p.name}
        subtitle={
          <>
            <Link to={`/c/${p.parent_category?.slug ?? p.category.slug}`} className="hover:underline">
              {p.parent_category?.name}
            </Link>
            {' › '}
            <Link to={`/c/${p.parent_category?.slug ?? p.category.slug}?sub=${p.category.slug}`} className="hover:underline">
              {p.category.name}
            </Link>
          </>
        }
      />
      <div className="grid grid-cols-1 gap-4 px-4 md:grid-cols-2 md:gap-8">
        <div className="relative grid aspect-[4/3] place-items-center rounded-3xl bg-white shadow-sm ring-1 ring-black/5 md:sticky md:top-[calc(var(--header-h)+16px)] md:aspect-square">
          {p.discount_percent > 0 && (
            <span className="absolute left-4 top-4 rounded-lg bg-[#256fef] px-2 py-1 text-xs font-extrabold text-white">{p.discount_percent}% OFF</span>
          )}
          <ProductImage product={p} size="lg" />
        </div>

        <div className="space-y-4">
          <div>
            {p.brand && <p className="text-sm font-semibold text-brand-700">{p.brand}</p>}
            <h1 className="text-2xl font-extrabold leading-tight">{p.name}</h1>
            <p className="mt-1 flex items-center gap-2 text-sm text-gray-500">
              {p.unit_label}
              <span
                className={cn('inline-grid size-4 place-items-center rounded-sm border-2', p.is_veg ? 'border-brand-600' : 'border-red-700')}
                title={p.is_veg ? 'Vegetarian' : 'Non-vegetarian'}
              >
                <span className={cn('size-1.5 rounded-full', p.is_veg ? 'bg-brand-600' : 'bg-red-700')} />
              </span>
            </p>
          </div>

          <div className="flex items-center justify-between rounded-2xl bg-white p-4 shadow-sm ring-1 ring-black/5">
            <div>
              <Price price={p.price} mrp={p.mrp} size="lg" />
              <p className="text-xs text-gray-500">(Inclusive of all taxes)</p>
            </div>
            <AddButton product={p} size="lg" />
          </div>

          <FulfillmentInfo product={p} />

          {p.description && (
            <Card>
              <h2 className="mb-1 font-bold">Product details</h2>
              <p className="text-sm text-gray-600">{p.description}</p>
              {aliases.length > 0 && (
                <p className="mt-2 text-sm text-gray-500">
                  <span className="font-semibold text-gray-700">Also searched as:</span> {aliases.join(', ')}
                </p>
              )}
              <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-gray-500">
                <BadgeCheck className="size-4 text-brand-600" /> 100% genuine · Easy returns at the store
              </p>
            </Card>
          )}
        </div>
      </div>

      {p.similar.length > 0 && (
        <section className="mt-8 px-4">
          <h2 className="mb-3 text-lg font-extrabold">Similar products</h2>
          <ProductRail products={p.similar} />
        </section>
      )}
    </div>
  )
}
