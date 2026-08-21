import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title: string
  subtitle?: string
  children?: React.ReactNode
  className?: string
}

export const Header = ({ title, subtitle, children, className }: HeaderProps) => {
  const { user } = useAuthStore()

  return (
    <header className={cn('flex items-start justify-between border-b border-line-200 pb-6', className)}>
      <div>
        <h1 className="font-display text-display text-ink-900">{title}</h1>
        {subtitle ? (
          <p className="mt-1 text-sm text-ink-400">{subtitle}</p>
        ) : null}
      </div>
      <div className="flex items-center gap-4">
        {children}
        {user ? (
          <div className="flex items-center gap-3 rounded-sm border border-line-200 bg-paper-100 px-3 py-2">
            <div className="h-6 w-6 rounded-sm bg-ink-900 flex items-center justify-center">
              <span className="text-xs font-sans font-medium text-paper-0">
                {user.full_name?.charAt(0) || user.email.charAt(0)}
              </span>
            </div>
            <div className="hidden md:block">
              <p className="text-xs font-sans font-medium text-ink-900">{user.full_name || user.email}</p>
              <p className="text-[10px] font-sans uppercase tracking-wider text-ink-400">{user.plan}</p>
            </div>
          </div>
        ) : null}
      </div>
    </header>
  )
}
