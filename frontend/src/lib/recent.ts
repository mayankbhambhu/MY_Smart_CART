const KEY = 'smartcart-recent-searches'

export function recentSearches(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(value) ? value.filter((v) => typeof v === 'string') : []
  } catch {
    return []
  }
}

export function rememberSearch(query: string) {
  const q = query.trim()
  if (q.length < 2) return
  try {
    const next = [q, ...recentSearches().filter((v) => v.toLowerCase() !== q.toLowerCase())].slice(0, 8)
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Storage unavailable (private mode): recent searches are just a convenience.
  }
}

export function clearRecentSearches() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}
