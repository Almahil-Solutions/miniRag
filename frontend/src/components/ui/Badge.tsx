import React from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'accent'
}

export const Badge = ({ className, variant = 'default', children, ...props }: BadgeProps) => {
  const variants = {
    default: 'bg-paper-0 text-ink-700 border-line-200',
    success: 'bg-success-600/10 text-success-600 border-success-600/20',
    warning: 'bg-warning-600/10 text-warning-600 border-warning-600/20',
    error: 'bg-error-600/10 text-error-600 border-error-600/20',
    accent: 'bg-accent-100 text-accent-700 border-accent-600/20',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-sans font-medium uppercase tracking-wider',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
