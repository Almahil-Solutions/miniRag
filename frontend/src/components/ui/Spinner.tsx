import { cn } from '@/lib/utils'

interface SpinnerProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export const Spinner = ({ className, size = 'md' }: SpinnerProps) => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  }

  return (
    <div className={cn('inline-block animate-spin rounded-full border-2 border-line-200 border-t-accent-600', sizes[size], className)} />
  )
}
