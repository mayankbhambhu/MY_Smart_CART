import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  Check,
  ChevronDown,
  ClipboardList,
  Copy,
  List,
  Map as MapIcon,
  MapPin,
  Mic,
  Minus,
  Plus,
  QrCode,
  Search,
  Smartphone,
  Trash2,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { StoreSheet } from '../components/LocationSheets'
import { ProductImage } from '../components/product'
import { StoreMap, type MapPin as Pin } from '../components/StoreMap'
import { Button, Card, Segmented, Sheet, Skeleton } from '../components/ui'
import { messageOf } from '../lib/api'
import { cn } from '../lib/cn'
import { formatINR, plural, shortStoreName, storeHours } from '../lib/format'
import { resolveShoppingList, useAppConfig, useInStoreCheckout, useStoreDetail, useStores } from '../lib/queries'
import { useShop } from '../lib/shop'
import type { Product, ResolvedItem, UnmatchedItem } from '../lib/types'
import { useVoiceInput } from '../lib/voice'
import { useAuth } from '../store/auth'
import { useInStore, useStoreList, type ListEntry } from '../store/instore'
import { useLocation } from '../store/location'
import { toast } from '../store/toast'

const EXAMPLES = ['2 milk, bread, 6 eggs, maggi', 'do doodh aur ek kilo cheeni', 'atta 5kg, toor dal, ghee, haldi']

function Stepper({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  return (
    <div className="flex h-8 w-[78px] items-center justify-between rounded-lg bg-indigo-600 text-sm font-bold text-white">
      <button type="button" onClick={() => onChange(value - 1)} className="grid h-full w-7 place-items-center" aria-label="Decrease quantity">
        {value === 1 ? <Trash2 className="size-3.5" /> : <Minus className="size-3.5" strokeWidth={3} />}
      </button>
      <span>{value}</span>
      <button type="button" onClick={() => onChange(value + 1)} className="grid h-full w-7 place-items-center" aria-label="Increase quantity">
        <Plus className="size-3.5" strokeWidth={3} />
      </button>
    </div>
  )
}

function ItemRow({
  item,
  picked,
  onToggle,
  onQty,
  onChange,
}: {
  item: ResolvedItem
  picked: boolean
  onToggle: () => void
  onQty: (qty: number) => void
  onChange: () => void
}) {
  const p = item.product
  const saidSomethingElse = !p.name.toLowerCase().includes(item.query.toLowerCase()) && item.query !== p.name
  return (
    <li className={cn('flex items-start gap-3 py-3 transition', picked && 'opacity-55')}>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={picked}
        aria-label={picked ? `Mark ${p.name} as not picked` : `Mark ${p.name} as picked`}
        className={cn(
          'mt-4 grid size-7 shrink-0 place-items-center rounded-full border-2 transition',
          picked ? 'border-brand-600 bg-brand-600 text-white' : 'border-gray-300 bg-white hover:border-indigo-400',
        )}
      >
        {picked && <Check className="size-4" strokeWidth={3} />}
      </button>
      <Link to={`/p/${p.id}/${p.slug}`} className="relative grid size-14 shrink-0 place-items-center rounded-xl bg-[#f5f6f8]">
        <ProductImage product={p} size="sm" />
        <span className="absolute -left-1.5 -top-1.5 grid size-5 place-items-center rounded-full bg-indigo-600 text-[10px] font-bold text-white ring-2 ring-white">
          {item.step}
        </span>
      </Link>
      <div className="min-w-0 flex-1">
        <p className={cn('line-clamp-2 text-sm font-semibold leading-snug', picked && 'line-through')}>{p.name}</p>
        <p className="mt-0.5 text-xs text-gray-500">
          {p.unit_label} · <span className="font-bold text-indigo-700">Row {p.location?.row}</span>
        </p>
        {!item.in_stock && <p className="mt-0.5 text-xs font-semibold text-red-600">Shelf shows empty · not in total</p>}
        {saidSomethingElse && <p className="mt-0.5 text-xs text-gray-400">You asked for "{item.query}"</p>}
        {item.alternatives.length > 0 && (
          <button type="button" onClick={onChange} className="mt-1 flex items-center gap-0.5 text-xs font-semibold text-indigo-700">
            {item.confidence < 80 ? 'Not this one? Change' : 'Change brand/size'} <ChevronDown className="size-3" />
          </button>
        )}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <p className="text-sm font-bold">{formatINR(item.line_total)}</p>
        <Stepper value={item.quantity} onChange={onQty} />
      </div>
    </li>
  )
}

function AlternativesSheet({ item, onClose, onPick }: { item: ResolvedItem | null; onClose: () => void; onPick: (product: Product) => void }) {
  return (
    <Sheet open={item != null} onClose={onClose} title={`Other options for "${item?.query ?? ''}"`}>
      <ul className="divide-y divide-gray-100">
        {item?.alternatives.map((alt) => (
          <li key={alt.id} className="flex items-center gap-3 py-3">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-[#f5f6f8]">
              <ProductImage product={alt} size="sm" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{alt.name}</p>
              <p className="text-xs text-gray-500">
                {alt.unit_label} · {formatINR(alt.price)} · {alt.location?.label}
                {alt.availability && !alt.availability.in_stock && <span className="text-red-600"> · out of stock</span>}
              </p>
            </div>
            <Button tone="secondary" className="h-9" onClick={() => onPick(alt)}>
              Choose
            </Button>
          </li>
        ))}
      </ul>
    </Sheet>
  )
}

function HowItWorks() {
  const steps = [
    { emoji: '🗣️', title: 'Tell us your list', body: 'Type it or tap the mic and say it — Hindi names work too.' },
    { emoji: '📍', title: 'See aisle & row', body: 'Every item gets its exact shelf, in the best walking order.' },
    { emoji: '🧾', title: 'Know your total', body: 'Live total as you shop. Pay at the counter or right in the app.' },
  ]
  return (
    <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {steps.map((step, i) => (
        <li key={step.title} className="flex gap-3 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-black/5 sm:flex-col">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-indigo-50 text-2xl">{step.emoji}</span>
          <div>
            <p className="font-bold">
              {i + 1}. {step.title}
            </p>
            <p className="text-sm text-gray-500">{step.body}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

export default function InStorePage() {
  const navigate = useNavigate()
  const token = useAuth((s) => s.token)
  const { store, storeId, mode } = useShop()
  const setMode = useLocation((s) => s.setMode)
  const entries = useStoreList(storeId)
  const lists = useInStore((s) => s.lists)
  const stores = useStores()
  const layout = useStoreDetail(storeId)
  const checkout = useInStoreCheckout(storeId)
  const payments = useAppConfig().data?.payments
  const payInApp = !payments?.online ? null : payments.provider === 'razorpay' ? (payments.test_mode ? 'UPI / card · test mode' : 'UPI / card') : 'test payment'
  const [params, setParams] = useSearchParams()

  const [text, setText] = useState('')
  const [view, setView] = useState<'list' | 'map'>('list')
  const [unmatched, setUnmatched] = useState<UnmatchedItem[]>([])
  const [storeSheet, setStoreSheet] = useState(false)
  const [changing, setChanging] = useState<ResolvedItem | null>(null)
  const [paying, setPaying] = useState(false)
  const voiceBase = useRef('')

  useEffect(() => {
    if (mode !== 'instore') setMode('instore')
  }, [mode, setMode])

  // Fresh locations, prices and the walking order for everything on the list.
  const located = useQuery({
    queryKey: ['instore-list', storeId, entries.map((e) => `${e.productId}x${e.quantity}`).join(',')],
    queryFn: () =>
      resolveShoppingList(storeId as number, {
        items: entries.map((e) => ({ query: e.query, quantity: e.quantity, product_id: e.productId })),
      }),
    enabled: storeId != null && entries.length > 0,
    placeholderData: keepPreviousData,
  })

  const find = useMutation({
    mutationFn: (input: { text?: string; entries?: ListEntry[] }) =>
      resolveShoppingList(storeId as number, {
        text: input.text,
        items: input.entries?.map((e) => ({ query: e.query, quantity: e.quantity, product_id: e.productId })),
      }),
    onSuccess: (result) => {
      if (storeId == null) return
      if (result.items.length) {
        useInStore.getState().addEntries(
          storeId,
          result.items.map((i) => ({ productId: i.product.id, query: i.query, quantity: i.quantity })),
        )
        toast(`Found ${plural(result.items.length, 'item')} in ${shortStoreName(result.store.name)}`, 'success')
        setView('list')
      }
      setUnmatched(result.unmatched)
      if (!result.items.length && result.unmatched.length) toast("Couldn't find that in this store", 'error')
      setText('')
    },
    onError: (error) => toast(messageOf(error), 'error'),
  })

  const voice = useVoiceInput((transcript, isFinal) => {
    const combined = [voiceBase.current, transcript].filter(Boolean).join(', ')
    setText(combined)
    if (isFinal && transcript && storeId != null) find.mutate({ text: combined })
  })
  const startVoice = () => {
    voiceBase.current = text.trim()
    voice.start()
  }

  // Arriving from the home screen with a list (?q=) or the mic (?voice=1): act on it once,
  // as soon as the store is known, then drop the parameter.
  useEffect(() => {
    if (storeId == null) return
    const q = params.get('q')
    const wantsVoice = params.get('voice')
    if (!q && !wantsVoice) return
    setParams({}, { replace: true })
    if (q) find.mutate({ text: q })
    else if (voice.supported) startVoice()
  }, [storeId]) // eslint-disable-line react-hooks/exhaustive-deps

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (text.trim() && storeId != null) find.mutate({ text: text.trim() })
  }

  const items = located.data?.items ?? []
  const picked = new Set(entries.filter((e) => e.picked).map((e) => e.productId))
  const pickedCount = items.filter((i) => picked.has(i.product.id)).length
  const otherList = Object.entries(lists).find(([id, list]) => Number(id) !== storeId && list.length > 0)
  const otherStore = otherList && stores.data?.find((s) => s.id === Number(otherList[0]))

  // Group the route into aisles (items arrive already sorted in walking order).
  const groups: { aisle: number; name: string | null; items: ResolvedItem[] }[] = []
  for (const item of items) {
    const aisle = item.product.location?.aisle ?? 0
    const last = groups[groups.length - 1]
    if (last && last.aisle === aisle) last.items.push(item)
    else groups.push({ aisle, name: item.product.location?.aisle_name ?? null, items: [item] })
  }

  const billItems = (pickedCount > 0 ? items.filter((i) => picked.has(i.product.id)) : items).filter((i) => i.quantity > 0)
  const billTotal = billItems.reduce((sum, i) => sum + i.product.price * i.quantity, 0)

  const pay = (method: 'pay_at_store' | 'online') => {
    if (storeId == null) return
    checkout.mutate(
      { items: billItems.map((i) => ({ product_id: i.product.id, quantity: i.quantity })), payment_method: method },
      {
        onSuccess: (order) => {
          useInStore.getState().clear(storeId)
          setPaying(false)
          // Paying in the app: the bill page opens Razorpay (or the test checkout) right away.
          navigate(`/orders/${order.id}?placed=1${order.payment_due ? '&pay=1' : ''}`)
        },
        onError: (error) => toast(messageOf(error), 'error'),
      },
    )
  }

  const pins: Pin[] = items
    .filter((i) => i.product.location)
    .map((i) => ({
      key: i.product.id,
      aisle: i.product.location!.aisle,
      row: i.product.location!.row,
      step: i.step,
      status: picked.has(i.product.id) ? 'picked' : i.in_stock ? 'todo' : 'missing',
      title: `${i.step}. ${i.product.name} — ${i.product.location!.label}`,
    }))

  return (
    <div className={cn('space-y-4 px-4 pt-4', items.length > 0 && 'pb-24')}>
      <div className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 p-4 text-white shadow-md">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-white/15">
          <MapPin className="size-6" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-100">You're shopping at Smart Cart</p>
          <p className="truncate text-lg font-extrabold leading-tight">{store ? shortStoreName(store.name) : 'Choose a store'}</p>
          {store && (
            <p className="truncate text-xs text-indigo-100">
              {storeHours(store)} · {layout.data ? plural(layout.data.aisles.length, 'aisle') : '…'}
            </p>
          )}
        </div>
        <button type="button" onClick={() => setStoreSheet(true)} className="shrink-0 rounded-lg bg-white/15 px-3 py-1.5 text-sm font-bold hover:bg-white/25">
          Change
        </button>
      </div>

      <Card>
        <form onSubmit={submit}>
          <label htmlFor="shopping-list" className="text-lg font-extrabold">
            What do you want to buy?
          </label>
          <p className="text-sm text-gray-500">Type or say your list. We'll find each item's aisle & row.</p>
          <div className={cn('mt-3 rounded-2xl border-2 bg-white transition', voice.listening ? 'border-indigo-500 ring-4 ring-indigo-100' : 'border-gray-200 focus-within:border-indigo-500')}>
            <textarea
              id="shopping-list"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) submit(e)
              }}
              rows={2}
              placeholder={voice.listening ? 'Listening… say "2 milk, bread and eggs"' : 'e.g. 2 milk, bread, 6 eggs, 1kg atta, maggi'}
              className="block w-full resize-none rounded-2xl bg-transparent px-4 pt-3 text-[15px] outline-none placeholder:text-gray-400"
            />
            <div className="flex items-center justify-between gap-2 px-2 pb-2">
              {voice.supported ? (
                <button
                  type="button"
                  onClick={voice.listening ? voice.stop : startVoice}
                  className={cn(
                    'flex h-10 items-center gap-2 rounded-xl px-3 text-sm font-bold transition',
                    voice.listening ? 'animate-pulse bg-red-500 text-white' : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100',
                  )}
                >
                  <Mic className="size-4" /> {voice.listening ? 'Listening… tap to stop' : 'Speak'}
                </button>
              ) : (
                <span className="px-2 text-xs text-gray-400">Voice input needs Chrome, Edge or Safari</span>
              )}
              <Button tone="indigo" type="submit" className="h-10" loading={find.isPending} disabled={!text.trim() || storeId == null}>
                <Search className="size-4" /> Find items
              </Button>
            </div>
          </div>
          {voice.error && <p className="mt-2 text-sm text-red-600">{voice.error}</p>}
        </form>
        {entries.length === 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => storeId != null && find.mutate({ text: example })}
                className="rounded-full bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-200"
              >
                Try "{example}"
              </button>
            ))}
          </div>
        )}
      </Card>

      {unmatched.length > 0 && (
        <Card className="border-l-4 border-amber-400">
          <div className="flex items-start justify-between gap-2">
            <h2 className="font-bold">Couldn't find {unmatched.length === 1 ? 'this' : 'these'} in this store</h2>
            <button type="button" onClick={() => setUnmatched([])} className="text-gray-400 hover:text-gray-600" aria-label="Dismiss">
              <X className="size-5" />
            </button>
          </div>
          <ul className="mt-2 space-y-3">
            {unmatched.map((u) => (
              <li key={u.query}>
                <p className="text-sm">
                  "<span className="font-semibold">{u.query}</span>"
                  {u.suggestions.length > 0 ? ' — did you mean:' : ' — ask a store associate'}
                </p>
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {u.suggestions.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => {
                        if (storeId == null) return
                        useInStore.getState().addEntries(storeId, [{ productId: s.id, query: u.query, quantity: u.quantity }])
                        setUnmatched((current) => current.filter((x) => x.query !== u.query))
                      }}
                      className="flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
                    >
                      <Plus className="size-3" /> {s.name} · {s.location?.label}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {entries.length === 0 ? (
        <>
          {otherList && otherStore && (
            <Card className="flex items-center gap-3">
              <ClipboardList className="size-6 shrink-0 text-indigo-600" />
              <p className="flex-1 text-sm">
                You have {plural(otherList[1].length, 'item')} on your list for <b>{shortStoreName(otherStore.name)}</b>.
              </p>
              <Button tone="secondary" className="h-9" loading={find.isPending} onClick={() => find.mutate({ entries: otherList[1] })}>
                <Copy className="size-4" /> Use here
              </Button>
            </Card>
          )}
          <HowItWorks />
        </>
      ) : located.isLoading ? (
        <Skeleton className="h-64" />
      ) : located.data ? (
        <>
          <Card className="bg-gradient-to-br from-white to-indigo-50/60">
            <div className="flex items-end justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Shopping total</p>
                <p className="text-3xl font-extrabold">{formatINR(located.data.total)}</p>
                {located.data.savings > 0 && <p className="text-sm font-semibold text-brand-700">You save {formatINR(located.data.savings)} vs MRP</p>}
              </div>
              <div className="text-right text-sm text-gray-600">
                <p>
                  <b>{plural(items.length, 'item')} on your list</b>
                </p>
                <p>{plural(located.data.route.length, 'aisle')} to visit</p>
              </div>
            </div>
            <div className="mt-3">
              <div className="flex justify-between text-xs font-semibold text-gray-500">
                <span>
                  Picked {pickedCount} of {items.length}
                </span>
                {located.data.out_of_stock_count > 0 && <span className="text-red-600">{located.data.out_of_stock_count} out of stock</span>}
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-indigo-100">
                <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${items.length ? (pickedCount / items.length) * 100 : 0}%` }} />
              </div>
            </div>
          </Card>

          <Segmented<'list' | 'map'>
            value={view}
            onChange={setView}
            options={[
              { value: 'list', label: <><List className="size-4" /> Aisle list</> },
              { value: 'map', label: <><MapIcon className="size-4" /> Store map</> },
            ]}
          />

          {view === 'list' ? (
            <div className="space-y-3">
              {groups.map((group) => (
                <Card key={group.aisle} className="py-2">
                  <h3 className="flex items-center gap-2 border-b border-gray-100 py-2">
                    <span className="grid size-9 place-items-center rounded-xl bg-indigo-600 text-sm font-extrabold text-white">{group.aisle}</span>
                    <span>
                      <span className="block font-bold leading-tight">Aisle {group.aisle}</span>
                      <span className="block text-xs text-gray-500">{group.name}</span>
                    </span>
                  </h3>
                  <ul className="divide-y divide-gray-100">
                    {group.items.map((item) => (
                      <ItemRow
                        key={item.product.id}
                        item={item}
                        picked={picked.has(item.product.id)}
                        onToggle={() => storeId != null && useInStore.getState().togglePicked(storeId, item.product.id)}
                        onQty={(qty) => storeId != null && useInStore.getState().setQty(storeId, item.product.id, qty)}
                        onChange={() => setChanging(item)}
                      />
                    ))}
                  </ul>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-3">
              {layout.data ? (
                <StoreMap aisles={layout.data.aisles} rows={layout.data.layout_rows} pins={pins} className="mx-auto max-w-3xl" />
              ) : (
                <Skeleton className="h-64" />
              )}
              <ol className="mt-3 space-y-1.5 text-sm">
                {items.map((item) => (
                  <li key={item.product.id} className={cn('flex items-center gap-2', picked.has(item.product.id) && 'text-gray-400 line-through')}>
                    <span className={cn('grid size-5 shrink-0 place-items-center rounded-full text-[10px] font-bold text-white', picked.has(item.product.id) ? 'bg-brand-600' : item.in_stock ? 'bg-indigo-600' : 'bg-gray-400')}>
                      {item.step}
                    </span>
                    <span className="min-w-0 flex-1 truncate">{item.product.name}</span>
                    <span className="shrink-0 font-semibold text-indigo-700">{item.product.location?.label}</span>
                  </li>
                ))}
              </ol>
            </Card>
          )}

          <button
            type="button"
            onClick={() => storeId != null && useInStore.getState().clear(storeId)}
            className="mx-auto flex items-center gap-1.5 text-sm font-semibold text-gray-500 hover:text-red-600"
          >
            <Trash2 className="size-4" /> Clear list
          </button>
        </>
      ) : null}

      {items.length > 0 && (
        <div
          style={{ bottom: 'var(--nav-h, 0px)' }}
          className="fixed inset-x-0 z-30 border-t border-black/5 bg-white/95 p-3 shadow-[0_-4px_16px_rgba(0,0,0,0.06)] backdrop-blur md:sticky md:inset-x-auto md:rounded-2xl md:border md:shadow-sm"
        >
          <div className="mx-auto flex max-w-6xl items-center gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-lg font-extrabold leading-tight">{formatINR(located.data?.total ?? 0)}</p>
              <p className="truncate text-xs text-gray-500">
                {pickedCount}/{items.length} picked · {located.data ? plural(located.data.route.length, 'aisle') : ''}
              </p>
            </div>
            <Button tone="indigo" className="h-12 px-5 text-base" onClick={() => (token ? setPaying(true) : navigate('/login?next=/instore'))}>
              Checkout <ArrowRight className="size-5" />
            </Button>
          </div>
        </div>
      )}

      <StoreSheet open={storeSheet} onClose={() => setStoreSheet(false)} purpose="instore" />
      <AlternativesSheet
        item={changing}
        onClose={() => setChanging(null)}
        onPick={(product) => {
          if (storeId != null && changing) useInStore.getState().swap(storeId, changing.product.id, product.id)
          setChanging(null)
        }}
      />
      <Sheet open={paying} onClose={() => setPaying(false)} title="Ready to pay?">
        <p className="text-sm text-gray-600">
          {pickedCount > 0
            ? `You'll be billed for the ${plural(pickedCount, 'item')} you've picked.`
            : `You'll be billed for all ${plural(billItems.length, 'item')} on your list.`}
        </p>
        <ul className="my-3 max-h-48 divide-y divide-gray-100 overflow-y-auto rounded-xl border border-gray-100 px-3">
          {billItems.map((i) => (
            <li key={i.product.id} className="flex justify-between gap-3 py-2 text-sm">
              <span className="truncate">
                {i.quantity} × {i.product.name}
              </span>
              <span className="shrink-0 font-semibold">{formatINR(i.product.price * i.quantity)}</span>
            </li>
          ))}
        </ul>
        <p className="flex justify-between text-lg font-extrabold">
          <span>Total</span>
          <span>{formatINR(billTotal)}</span>
        </p>
        <div className="mt-4 grid gap-2">
          <Button tone="indigo" className="h-12" loading={checkout.isPending} onClick={() => pay('pay_at_store')}>
            <QrCode className="size-5" /> Pay at the counter
          </Button>
          {payInApp && (
            <Button tone="secondary" className="h-12" disabled={checkout.isPending} onClick={() => pay('online')}>
              <Smartphone className="size-5" /> Pay now in the app
              <span className="text-xs font-normal text-gray-500">· {payInApp}</span>
            </Button>
          )}
        </div>
        <p className="mt-3 text-center text-xs text-gray-500">At the counter, show the bill QR — the cashier scans it, no re-scanning items.</p>
      </Sheet>
    </div>
  )
}
