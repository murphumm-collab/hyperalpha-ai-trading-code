import Cookies from 'js-cookie'

export function withAuthHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers(headers)
  const token = Cookies.get('arena_token')

  if (token && !merged.has('Authorization')) {
    merged.set('Authorization', `Bearer ${token}`)
  }

  return merged
}

export function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  return fetch(input, {
    ...init,
    credentials: init.credentials ?? 'include',
    headers: withAuthHeaders(init.headers),
  })
}
