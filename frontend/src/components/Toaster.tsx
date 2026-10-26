import { CircleCheck, Info, TriangleAlert } from 'lucide-react'

import { cn } from '../lib/cn'
import { useToasts } from '../store/toast'

const ICONS = { success: CircleCheck, error: TriangleAlert, info: Info }

export function Toaster() {
  const toasts = useToasts((s) => s.toasts)
  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-36 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-8"
      aria-live="polite"
    >
      {toasts.map((t) => {
        const Icon = ICONS[t.tone]
        return (
          <div
            key={t.id}
            className={cn(
              'pointer-events-auto flex max-w-sm animate-slide-up items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-lg',
              t.tone === 'error' ? 'bg-red-600' : 'bg-gray-900',
            )}
          >
            <Icon className={cn('size-4 shrink-0', t.tone === 'success' && 'text-brand-300')} aria-hidden />
            {t.message}
          </div>
        )
      })}
    </div>
  )
}
