import type { ComponentType } from 'react'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { AppShell } from './components/layout'
import { Spinner } from './components/ui'
import CategoriesPage from './pages/CategoriesPage'
import CategoryPage from './pages/CategoryPage'
import HomePage from './pages/HomePage'
import NotFoundPage from './pages/NotFoundPage'
import ProductPage from './pages/ProductPage'
import SearchPage from './pages/SearchPage'

// Browsing pages load up front; the rest are split into their own chunks.
const page = (load: () => Promise<{ default: ComponentType }>) => async () => ({ Component: (await load()).default })

const router = createBrowserRouter([
  {
    path: '/',
    Component: AppShell,
    HydrateFallback: Spinner,
    children: [
      { index: true, Component: HomePage },
      { path: 'categories', Component: CategoriesPage },
      { path: 'c/:slug', Component: CategoryPage },
      { path: 'search', Component: SearchPage },
      { path: 'p/:id/:slug?', Component: ProductPage },
      { path: 'cart', lazy: page(() => import('./pages/CartPage')) },
      { path: 'instore', lazy: page(() => import('./pages/InStorePage')) },
      { path: 'orders', lazy: page(() => import('./pages/OrdersPage')) },
      { path: 'orders/:id', lazy: page(() => import('./pages/OrderDetailPage')) },
      { path: 'login', lazy: page(() => import('./pages/LoginPage')) },
      { path: 'account', lazy: page(() => import('./pages/AccountPage')) },
      { path: 'addresses', lazy: page(() => import('./pages/AddressesPage')) },
      { path: 'staff', lazy: page(() => import('./pages/StaffPage')) },
      { path: '*', Component: NotFoundPage },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
