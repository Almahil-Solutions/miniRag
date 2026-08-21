import React from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const base =
      'inline-flex items-center justify-center font-sans font-medium transition-colors duration-150 ease-out focus:outline-none focus:ring-2 focus:ring-accent-600/30 disabled:opacity-50 disabled:cursor-not-allowed'

    const variants = {
      primary:
        'bg-ink-900 text-paper-0 hover:bg-ink-700 active:bg-ink-900',
      secondary:
        'bg-paper-100 text-ink-900 border border-line-200 hover:bg-paper-0 hover:border-ink-400 active:bg-paper-100',
      ghost:
        'bg-transparent text-ink-700 hover:bg-paper-100 hover:text-ink-900 active:bg-paper-0',
      danger:
        'bg-error-600 text-paper-0 hover:opacity-90 active:opacity-100',
    }

    const sizes = {
      sm: 'text-xs px-3 py-1.5 rounded-sm',
      md: 'text-sm px-4 py-2 rounded-sm',
      lg: 'text-body px-5 py-2.5 rounded-sm',
    }

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <span className="mr-2 inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
        ) : null}
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'
