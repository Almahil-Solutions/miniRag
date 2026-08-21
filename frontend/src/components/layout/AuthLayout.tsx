import { Outlet } from 'react-router-dom'
import { Hexagon } from 'lucide-react'

export const AuthLayout = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper-0 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-3">
          <Hexagon className="h-8 w-8 text-ink-900 stroke-[1.5]" />
          <div className="flex flex-col">
            <span className="font-display text-2xl font-medium leading-none text-ink-900 tracking-tight">
              Kayan
            </span>
            <span className="text-xs font-sans font-medium uppercase tracking-wider text-ink-400 leading-none mt-1">
              Index
            </span>
          </div>
        </div>
        <Outlet />
      </div>
    </div>
  )
}
