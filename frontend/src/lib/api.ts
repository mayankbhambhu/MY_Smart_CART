import { useAuth } from '../store/auth'

export class ApiError extends Error {
  status: number
  details: unknown

  constructor(status: number, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

type Params = Record<string, string | number | boolean | null | undefined>

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  params?: Params
  signal?: AbortSignal
}

const BASE_URL: string = import.meta.env.VITE_API_URL ?? '/api'

function errorMessage(data: unknown, status: number): string {
  const detail = (data as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') {
    return detail[0].msg.replace(/^Value error, /, '')
  }
  if (status >= 500) return 'Something went wrong on our side. Please try again.'
  return `Request failed (${status})`
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(BASE_URL + path, window.location.origin)
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  }

  const token = useAuth.getState().token
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(url, {
      method: options.method ?? (options.body !== undefined ? 'POST' : 'GET'),
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new ApiError(0, "Can't reach Smart Cart. Check your connection and try again.")
  }

  if (response.status === 204) return undefined as T
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && token) useAuth.getState().logout()
    throw new ApiError(response.status, errorMessage(data, response.status), (data as { details?: unknown })?.details)
  }
  return data as T
}

export function messageOf(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}
