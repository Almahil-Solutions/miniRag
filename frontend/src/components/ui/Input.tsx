import React from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label ? (
          <label className="mb-1.5 block text-xs font-sans font-medium uppercase tracking-wider text-ink-400">
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          className={cn(
            'w-full rounded-sm border border-line-200 bg-paper-100 px-3 py-2 text-sm font-sans text-ink-900 placeholder:text-ink-400',
            'focus:border-accent-600 focus:outline-none focus:ring-1 focus:ring-accent-600/20',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-error-600 focus:border-error-600 focus:ring-error-600/20',
            className
          )}
          {...props}
        />
        {error ? (
          <p className="mt-1 text-xs text-error-600">{error}</p>
        ) : null}
      </div>
    )
  }
)
Input.displayName = 'Input'
