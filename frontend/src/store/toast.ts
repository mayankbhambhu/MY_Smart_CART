import { create } from 'zustand'

export type ToastTone = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  tone: ToastTone
}

interface ToastState {
  toasts: Toast[]
  show: (message: string, tone?: ToastTone) => void
  dismiss: (id: number) => void
}

let nextId = 1

export const useToasts = create<ToastState>()((set, get) => ({
  toasts: [],
  show: (message, tone = 'info') => {
    const id = nextId++
    set({ toasts: [...get().toasts.slice(-2), { id, message, tone }] })
    window.setTimeout(() => get().dismiss(id), 2600)
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}))

export const toast = (message: string, tone?: ToastTone) => useToasts.getState().show(message, tone)
