import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useLogin } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { AlertCircle } from 'lucide-react'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type FormData = z.infer<typeof schema>

export const LoginPage = () => {
  const login = useLogin()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await login.mutateAsync(data)
      window.location.href = '/'
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password.')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-h2 text-ink-900">Sign in</h2>
        <p className="mt-1 text-sm text-ink-400">Access your knowledge index.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@company.com"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          error={errors.password?.message}
          {...register('password')}
        />

        {error ? (
          <div className="flex items-center gap-2 rounded-sm border border-error-600/20 bg-error-600/5 px-3 py-2 text-sm text-error-600">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        ) : null}

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full"
          isLoading={login.isPending}
        >
          Sign in
        </Button>
      </form>

      <p className="text-center text-sm text-ink-400">
        No account?{' '}
        <Link to="/register" className="font-medium text-accent-700 hover:underline">
          Create one
        </Link>
      </p>
    </div>
  )
}
