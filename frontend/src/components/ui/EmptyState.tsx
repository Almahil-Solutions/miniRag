import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  className?: string
}

export const EmptyState = ({ icon: Icon, title, description, className }: EmptyStateProps) => (
  <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
    <Icon className="h-8 w-8 text-ink-400 stroke-[1.5]" />
    <h3 className="mt-4 text-h3 font-sans font-semibold text-ink-900">{title}</h3>
    {description ? (
      <p className="mt-2 max-w-sm text-sm text-ink-400">{description}</p>
    ) : null}
  </div>
)
