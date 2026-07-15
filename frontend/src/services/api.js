import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api'

const apiClient = axios.create({
  baseURL: API_BASE,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('ppa_token')
  if (token) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    }
  }
  // Prevent the browser from serving a stale cached GET (e.g. an empty
  // drives list captured before a drive was approved). A unique query param
  // busts the cache without adding a request header (which would trigger a
  // CORS preflight the API doesn't allow).
  if (!config.method || config.method.toLowerCase() === 'get') {
    config.params = { ...(config.params || {}), _t: Date.now() }
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('ppa_token')
      localStorage.removeItem('ppa_user')
      if (window.location.pathname !== '/') {
        // Tell the user why they are being sent back to login instead of
        // silently dropping them there (token expired / invalid session).
        window.alert('Your session has expired. Please log in again.')
        window.location.href = '/'
      }
    }
    return Promise.reject(error)
  },
)

export function apiRequest(path, options = {}) {
  return apiClient({
    url: path,
    ...options,
  })
}
