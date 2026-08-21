import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { useAuthInit } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

export const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuthStore()
  const { isLoading: isUserLoading } = useAuthInit()

  if (isLoading || isUserLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-paper-0">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
