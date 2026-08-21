import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  History,
  UserCircle,
  ShieldCheck,
  LogOut,
  Hexagon,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

const navItems = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'History', path: '/history', icon: History },
  { label: 'Profile', path: '/profile', icon: UserCircle },
]

const adminItem = { label: 'Admin', path: '/admin/users', icon: ShieldCheck }

export const Sidebar = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAdmin, logout } = useAuthStore()

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <aside className="flex h-screen w-[280px] flex-col border-r border-line-200 bg-paper-100">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-line-200 px-6">
        <Hexagon className="h-6 w-6 text-ink-900 stroke-[1.5]" />
        <div className="flex flex-col">
          <span className="font-display text-lg font-medium leading-none text-ink-900 tracking-tight">
            Kayan
          </span>
          <span className="text-[10px] font-sans font-medium uppercase tracking-wider text-ink-400 leading-none mt-0.5">
            Index
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-4 py-6">
        <div className="space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-sm px-3 py-2 text-sm font-sans font-medium transition-colors duration-150',
                isActive(item.path)
                  ? 'bg-accent-100 text-accent-700'
                  : 'text-ink-700 hover:bg-paper-0 hover:text-ink-900'
              )}
            >
              <item.icon className="h-4 w-4 stroke-[1.5]" />
              {item.label}
            </Link>
          ))}
          {isAdmin && (
            <Link
              to={adminItem.path}
              className={cn(
                'flex items-center gap-3 rounded-sm px-3 py-2 text-sm font-sans font-medium transition-colors duration-150',
                isActive(adminItem.path)
                  ? 'bg-accent-100 text-accent-700'
                  : 'text-ink-700 hover:bg-paper-0 hover:text-ink-900'
              )}
            >
              <adminItem.icon className="h-4 w-4 stroke-[1.5]" />
              {adminItem.label}
            </Link>
          )}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-line-200 p-4">
        <button
          onClick={() => {
            logout()
            navigate('/login')
          }}
          className="flex w-full items-center gap-3 rounded-sm px-3 py-2 text-sm font-sans font-medium text-ink-400 transition-colors hover:bg-paper-0 hover:text-ink-700"
        >
          <LogOut className="h-4 w-4 stroke-[1.5]" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
