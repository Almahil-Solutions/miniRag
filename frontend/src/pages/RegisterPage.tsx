import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRegister, useLogin } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  full_name: z.string().optional(),
})

type FormData = z.infer<typeof schema>

export const RegisterPage = () => {
  const registerMutation = useRegister()
  const login = useLogin()
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

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
      await registerMutation.mutateAsync(data)
      await login.mutateAsync({ email: data.email, password: data.password })
      setSuccess(true)
      window.location.href = '/'
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError('This email is already registered.')
      } else {
        setError(err.response?.data?.detail || 'Registration failed. Please try again.')
      }
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-h2 text-ink-900">Create account</h2>
        <p className="mt-1 text-sm text-ink-400">Set up your knowledge index.</p>
      </div>

      {success ? (
        <div className="flex items-center gap-2 rounded-sm border border-success-600/20 bg-success-600/5 px-3 py-2 text-sm text-success-600">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Account created. Redirecting...
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Full name"
            placeholder="Jane Doe"
            error={errors.full_name?.message}
            {...register('full_name')}
          />
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
            placeholder="Minimum 8 characters"
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
            isLoading={registerMutation.isPending || login.isPending}
          >
            Create account
          </Button>
        </form>
      )}

      <p className="text-center text-sm text-ink-400">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent-700 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  )
}
