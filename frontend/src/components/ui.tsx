import { ArrowLeft, LoaderCircle, RefreshCw, X } from 'lucide-react'
import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router'

import { messageOf } from '../lib/api'
import { cn } from '../lib/cn'

type ButtonTone = 'primary' | 'secondary' | 'ghost' | 'danger' | 'indigo' | 'amber'

const TONES: Record<ButtonTone, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-gray-300',
  secondary: 'border border-gray-200 bg-white text-ink hover:bg-gray-50 disabled:text-gray-400',
  ghost: 'text-brand-700 hover:bg-brand-50 disabled:text-gray-400',
  danger: 'border border-red-200 bg-white text-red-600 hover:bg-red-50 disabled:text-red-300',
  indigo: 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-gray-300',
  amber: 'bg-amber-500 text-white hover:bg-amber-600 disabled:bg-gray-300',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: ButtonTone
  loading?: boolean
  block?: boolean
}

export function Button({ tone = 'primary', loading, block, className, children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || loading}
      className={cn(
        'inline-flex h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed',
        TONES[tone],
        block && 'w-full',
        className,
      )}
    >
      {loading && <LoaderCircle className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-gray-400" role="status">
      <LoaderCircle className="size-7 animate-spin" aria-hidden />
      <span className="sr-only">{label}</span>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-xl bg-gray-200/70', className)} />
}

export function EmptyState({
  emoji,
  title,
  body,
  action,
}: {
  emoji: string
  title: string
  body?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-6 py-16 text-center">
      <div className="mb-4 grid size-24 place-items-center rounded-full bg-white text-5xl shadow-sm">{emoji}</div>
      <h2 className="text-lg font-bold">{title}</h2>
      {body && <p className="mt-1 max-w-sm text-sm text-gray-500">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <EmptyState
      emoji="😕"
      title="Something went wrong"
      body={messageOf(error)}
      action={
        onRetry && (
          <Button tone="secondary" onClick={onRetry}>
            <RefreshCw className="size-4" /> Try again
          </Button>
        )
      }
    />
  )
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: ReactNode; right?: ReactNode }) {
  const navigate = useNavigate()
  return (
    <div className="flex items-center gap-3 px-4 pb-2 pt-4">
      <button
        type="button"
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
        className="grid size-9 shrink-0 place-items-center rounded-full bg-white shadow-sm ring-1 ring-black/5 hover:bg-gray-50"
        aria-label="Go back"
      >
        <ArrowLeft className="size-5" />
      </button>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-bold leading-tight">{title}</h1>
        {subtitle && <p className="truncate text-xs text-gray-500">{subtitle}</p>}
      </div>
      {right}
    </div>
  )
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-2xl bg-white p-4 shadow-sm ring-1 ring-black/5', className)}>{children}</section>
}

export function Sheet({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [open, onClose])

  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 animate-fade-in bg-black/45" onClick={onClose} />
      <div className="relative flex max-h-[88dvh] w-full max-w-lg animate-slide-up flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl sm:rounded-3xl">
        <header className="flex items-center justify-between gap-3 border-b border-gray-100 px-5 py-4">
          <h2 className="text-lg font-bold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="grid size-8 place-items-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </header>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="border-t border-gray-100 p-4">{footer}</div>}
      </div>
    </div>,
    document.body,
  )
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: T
  options: { value: T; label: ReactNode }[]
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div className={cn('flex rounded-xl bg-gray-100 p-1', className)} role="tablist">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="tab"
          aria-selected={value === option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition',
            value === option.value ? 'bg-white text-ink shadow-sm' : 'text-gray-500 hover:text-ink',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
