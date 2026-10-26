import { useQueryClient } from '@tanstack/react-query'
import { ChevronRight, LayoutDashboard, LogOut, MapPin, Pencil, ReceiptText, Store } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Button, Card, EmptyState, PageHeader } from '../components/ui'
import { messageOf } from '../lib/api'
import { formatPhone } from '../lib/format'
import { useUpdateProfile } from '../lib/queries'
import { isStaff, useAuth } from '../store/auth'
import { PRESET_PLACES, useLocation } from '../store/location'
import { toast } from '../store/toast'

export default function AccountPage() {
  const navigate = useNavigate()
  const client = useQueryClient()
  const { user, logout } = useAuth()
  const setPlace = useLocation((s) => s.setPlace)
  const update = useUpdateProfile()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(user?.name ?? '')

  if (!user) {
    return (
      <div>
        <PageHeader title="Account" />
        <EmptyState
          emoji="👋"
          title="Log in to Smart Cart"
          body="Save addresses, schedule pickups and keep your in-store bills in one place."
          action={
            <Link to="/login?next=/account">
              <Button>Log in with phone</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const saveName = (event: FormEvent) => {
    event.preventDefault()
    update.mutate(
      { name: name.trim() },
      {
        onSuccess: () => {
          setEditing(false)
          toast('Name updated', 'success')
        },
        onError: (error) => toast(messageOf(error), 'error'),
      },
    )
  }

  const links = [
    { to: '/orders', label: 'My orders', hint: 'Deliveries, pickups & in-store bills', icon: ReceiptText },
    { to: '/addresses', label: 'Saved addresses', hint: 'Where we deliver', icon: MapPin },
    { to: '/instore', label: 'In-store shopping', hint: 'Find aisle & row for your list', icon: Store },
    ...(isStaff(user) ? [{ to: '/staff', label: 'Store dashboard', hint: 'Manage orders, pickups & bills', icon: LayoutDashboard }] : []),
  ]

  return (
    <div className="space-y-4 px-4 pt-4">
      <Card className="flex items-center gap-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-full bg-brand-600 text-2xl font-bold text-white">
          {(user.name ?? 'S').charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          {editing ? (
            <form onSubmit={saveName} className="flex gap-2">
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={80}
                className="h-10 min-w-0 flex-1 rounded-lg border border-gray-300 px-3 outline-none focus:border-brand-600"
                aria-label="Your name"
              />
              <Button type="submit" className="h-10" loading={update.isPending}>
                Save
              </Button>
            </form>
          ) : (
            <p className="flex items-center gap-2 text-lg font-bold">
              {user.name ?? 'Add your name'}
              <button type="button" onClick={() => setEditing(true)} className="text-gray-400 hover:text-gray-700" aria-label="Edit name">
                <Pencil className="size-4" />
              </button>
            </p>
          )}
          <p className="text-sm text-gray-500">{formatPhone(user.phone)}</p>
          {user.role !== 'customer' && (
            <span className="mt-1 inline-block rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-bold capitalize text-indigo-700">{user.role}</span>
          )}
        </div>
      </Card>

      <Card className="p-2">
        <ul>
          {links.map(({ to, label, hint, icon: Icon }) => (
            <li key={to}>
              <Link to={to} className="flex items-center gap-3 rounded-xl px-3 py-3 hover:bg-gray-50">
                <span className="grid size-10 place-items-center rounded-xl bg-gray-100">
                  <Icon className="size-5 text-gray-700" />
                </span>
                <span className="flex-1">
                  <span className="block font-semibold">{label}</span>
                  <span className="block text-xs text-gray-500">{hint}</span>
                </span>
                <ChevronRight className="size-5 text-gray-400" />
              </Link>
            </li>
          ))}
        </ul>
      </Card>

      <Button
        tone="danger"
        block
        onClick={() => {
          logout()
          client.clear()
          setPlace(PRESET_PLACES[0])
          navigate('/')
          toast('Logged out')
        }}
      >
        <LogOut className="size-4" /> Log out
      </Button>
      <p className="pb-4 text-center text-xs text-gray-400">Smart Cart · v0.1</p>
    </div>
  )
}
