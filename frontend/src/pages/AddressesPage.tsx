import { Briefcase, House, LocateFixed, MapPin, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState, type FormEvent, type InputHTMLAttributes } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { Button, Card, EmptyState, PageHeader, Spinner } from '../components/ui'
import { messageOf } from '../lib/api'
import { cn } from '../lib/cn'
import { useAddresses, useDeleteAddress, useSaveAddress } from '../lib/queries'
import type { Address, AddressInput } from '../lib/types'
import { useAuth } from '../store/auth'
import { useLocation } from '../store/location'
import { toast } from '../store/toast'

const LABEL_ICONS = { Home: House, Work: Briefcase, Other: MapPin }

function Field({ label, ...input }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-gray-600">{label}</span>
      <input
        {...input}
        className="h-11 w-full rounded-xl border border-gray-300 px-3 outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
      />
    </label>
  )
}

function AddressForm({ initial, onDone }: { initial?: Address; onDone: (saved: Address) => void }) {
  const user = useAuth((s) => s.user)
  const location = useLocation()
  const save = useSaveAddress()
  const [locating, setLocating] = useState(false)
  const [form, setForm] = useState<AddressInput>(
    initial ?? {
      label: 'Home',
      receiver_name: user?.name ?? '',
      receiver_phone: user?.phone ?? '',
      house: '',
      area: '',
      landmark: '',
      city: 'Gurugram',
      pincode: '',
      lat: location.lat,
      lng: location.lng,
      is_default: false,
    },
  )
  const set = <K extends keyof AddressInput>(key: K, value: AddressInput[K]) => setForm((f) => ({ ...f, [key]: value }))

  const locate = () => {
    if (!navigator.geolocation) return toast("Your browser can't share location", 'error')
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        setForm((f) => ({ ...f, lat: pos.coords.latitude, lng: pos.coords.longitude }))
        toast('Pinned to your current location', 'success')
      },
      () => {
        setLocating(false)
        toast('Could not get your location', 'error')
      },
    )
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(
      { ...form, id: initial?.id, landmark: form.landmark || null, receiver_phone: form.receiver_phone || null },
      { onSuccess: onDone, onError: (error) => toast(messageOf(error), 'error') },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex gap-2">
        {(['Home', 'Work', 'Other'] as const).map((label) => {
          const Icon = LABEL_ICONS[label]
          return (
            <button
              key={label}
              type="button"
              onClick={() => set('label', label)}
              className={cn(
                'flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold',
                form.label === label ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-gray-200',
              )}
            >
              <Icon className="size-4" /> {label}
            </button>
          )
        })}
      </div>
      <Field label="Flat / House no. / Building *" required value={form.house} onChange={(e) => set('house', e.target.value)} maxLength={120} />
      <Field label="Area / Sector / Locality *" required value={form.area} onChange={(e) => set('area', e.target.value)} maxLength={160} />
      <Field label="Landmark (optional)" value={form.landmark ?? ''} onChange={(e) => set('landmark', e.target.value)} maxLength={120} />
      <div className="grid grid-cols-2 gap-3">
        <Field label="City *" required value={form.city} onChange={(e) => set('city', e.target.value)} maxLength={60} />
        <Field
          label="Pincode *"
          required
          inputMode="numeric"
          pattern="\d{6}"
          title="6-digit pincode"
          value={form.pincode}
          onChange={(e) => set('pincode', e.target.value.replace(/\D/g, '').slice(0, 6))}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Receiver's name *" required value={form.receiver_name} onChange={(e) => set('receiver_name', e.target.value)} maxLength={80} />
        <Field
          label="Receiver's phone"
          inputMode="numeric"
          value={form.receiver_phone ?? ''}
          onChange={(e) => set('receiver_phone', e.target.value.replace(/\D/g, '').slice(0, 10))}
        />
      </div>
      <div className="flex items-center justify-between gap-3 rounded-xl bg-gray-50 px-3 py-2.5 text-sm">
        <span className="text-gray-600">
          Map pin: {form.lat.toFixed(4)}, {form.lng.toFixed(4)}
        </span>
        <button type="button" onClick={locate} className="flex shrink-0 items-center gap-1 font-semibold text-brand-700">
          <LocateFixed className={cn('size-4', locating && 'animate-pulse')} /> Use GPS
        </button>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.is_default} onChange={(e) => set('is_default', e.target.checked)} className="size-4 accent-brand-600" />
        Make this my default address
      </label>
      <Button type="submit" block className="h-12" loading={save.isPending}>
        Save address
      </Button>
    </form>
  )
}

export default function AddressesPage() {
  const token = useAuth((s) => s.token)
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next')
  const addresses = useAddresses()
  const remove = useDeleteAddress()
  const setPlace = useLocation((s) => s.setPlace)
  const [editing, setEditing] = useState<Address | 'new' | null>(params.get('new') ? 'new' : null)

  if (!token) {
    return (
      <div>
        <PageHeader title="Saved addresses" />
        <EmptyState
          emoji="📍"
          title="Log in to save addresses"
          action={
            <Link to="/login?next=/addresses">
              <Button>Log in</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const done = (saved: Address) => {
    setPlace({ label: `${saved.label} · ${saved.area}`, lat: saved.lat, lng: saved.lng, addressId: saved.id })
    toast('Address saved', 'success')
    setEditing(null)
    if (next?.startsWith('/')) navigate(next)
  }

  return (
    <div>
      <PageHeader
        title={editing ? (editing === 'new' ? 'Add address' : 'Edit address') : 'Saved addresses'}
        right={
          !editing && (
            <Button tone="ghost" className="h-9" onClick={() => setEditing('new')}>
              <Plus className="size-4" /> Add
            </Button>
          )
        }
      />
      <div className="px-4">
        {editing ? (
          <Card>
            <AddressForm initial={editing === 'new' ? undefined : editing} onDone={done} />
            <button type="button" onClick={() => setEditing(null)} className="mt-3 w-full text-center text-sm font-semibold text-gray-500">
              Cancel
            </button>
          </Card>
        ) : addresses.isLoading ? (
          <Spinner />
        ) : addresses.data?.length === 0 ? (
          <EmptyState emoji="🏠" title="No saved addresses" body="Add one to get groceries delivered." action={<Button onClick={() => setEditing('new')}>Add address</Button>} />
        ) : (
          <ul className="space-y-3">
            {addresses.data?.map((a) => {
              const Icon = LABEL_ICONS[a.label] ?? MapPin
              return (
                <li key={a.id}>
                  <Card className="flex items-start gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gray-100">
                      <Icon className="size-5 text-gray-700" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center gap-2 font-bold">
                        {a.label}
                        {a.is_default && <span className="rounded bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-brand-700">Default</span>}
                      </p>
                      <p className="text-sm text-gray-600">
                        {a.house}, {a.area}
                        {a.landmark ? `, ${a.landmark}` : ''}, {a.city} {a.pincode}
                      </p>
                      <p className="text-xs text-gray-400">
                        {a.receiver_name}
                        {a.receiver_phone ? ` · ${a.receiver_phone}` : ''}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <button type="button" onClick={() => setEditing(a)} className="grid size-9 place-items-center rounded-lg hover:bg-gray-100" aria-label={`Edit ${a.label} address`}>
                        <Pencil className="size-4 text-gray-600" />
                      </button>
                      <button
                        type="button"
                        onClick={() => remove.mutate(a.id, { onSuccess: () => toast('Address deleted') })}
                        className="grid size-9 place-items-center rounded-lg hover:bg-red-50"
                        aria-label={`Delete ${a.label} address`}
                      >
                        <Trash2 className="size-4 text-red-500" />
                      </button>
                    </div>
                  </Card>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
