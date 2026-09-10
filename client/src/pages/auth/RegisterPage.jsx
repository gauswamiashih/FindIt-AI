/**
 * Register Page with Supabase Google Login support
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { User, Mail, Lock, Eye, EyeOff, UserPlus, Phone } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useAuth } from '../../context/AuthContext'
import { Input, Button } from '../../components/ui'
import { useDocumentTitle } from '../../hooks/index'

const schema = z.object({
  name:            z.string().min(2, 'Name must be at least 2 characters'),
  email:           z.string().email('Please enter a valid email'),
  password:        z.string().min(8, 'Password must be at least 8 characters')
                    .regex(/[A-Z]/, 'Must contain an uppercase letter')
                    .regex(/[0-9]/, 'Must contain a number'),
  confirmPassword: z.string(),
  phone:           z.string().optional(),
}).refine((d) => d.password === d.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
})

export default function RegisterPage() {
  useDocumentTitle('Create Account')
  const { register: signup, loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [showPwd,    setShowPwd]    = useState(false)
  const [showConfirm,setShowConfirm]= useState(false)
  const [loading,    setLoading]    = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await signup({
        name: data.name,
        email: data.email,
        password: data.password,
        phone: data.phone,
      })
      toast.success('Account created successfully! 🎉')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      toast.error(err.message || err.response?.data?.detail || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    setGoogleLoading(true)
    try {
      await loginWithGoogle()
    } catch (err) {
      toast.error(err.message || 'Failed to initialize Google login.')
      setGoogleLoading(false)
    }
  }

  return (
    <div>
      <div className="text-center mb-8">
        <h2 className="text-2xl font-black mb-2">Create your account</h2>
        <p className="text-dark-100/50 text-sm">Join FindIt and recover what's yours</p>
      </div>

      {/* Google OAuth Register/Login */}
      <button
        type="button"
        onClick={handleGoogleLogin}
        disabled={googleLoading || loading}
        className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-800 font-semibold py-2.5 px-4 border border-gray-300 rounded-lg shadow-sm transition-all text-sm mb-6 disabled:opacity-50"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
          />
        </svg>
        {googleLoading ? 'Connecting to Google...' : 'Continue with Google'}
      </button>

      <div className="relative flex py-2 items-center mb-6">
        <div className="flex-grow border-t border-dark-300"></div>
        <span className="flex-shrink mx-4 text-dark-100/40 text-xs font-semibold uppercase">Or with Email</span>
        <div className="flex-grow border-t border-dark-300"></div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Full Name"
          type="text"
          placeholder="John Doe"
          icon={<User size={16} />}
          error={errors.name?.message}
          id="register-name"
          {...register('name')}
        />

        <Input
          label="Email Address"
          type="email"
          placeholder="you@example.com"
          icon={<Mail size={16} />}
          error={errors.email?.message}
          id="register-email"
          {...register('email')}
        />

        <Input
          label="Phone (optional)"
          type="tel"
          placeholder="+1 234 567 8900"
          icon={<Phone size={16} />}
          error={errors.phone?.message}
          id="register-phone"
          {...register('phone')}
        />

        {/* Password */}
        <div className="space-y-1.5">
          <label className="label">Password</label>
          <div className="relative">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-200/50" />
            <input
              type={showPwd ? 'text' : 'password'}
              placeholder="Min 8 chars, 1 uppercase, 1 number"
              className={`input pl-9 pr-10 ${errors.password ? 'input-error' : ''}`}
              id="register-password"
              {...register('password')}
            />
            <button type="button" onClick={() => setShowPwd(!showPwd)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-200/50">
              {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.password && <p className="text-danger-400 text-xs">{errors.password.message}</p>}
        </div>

        {/* Confirm Password */}
        <div className="space-y-1.5">
          <label className="label">Confirm Password</label>
          <div className="relative">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-200/50" />
            <input
              type={showConfirm ? 'text' : 'password'}
              placeholder="Repeat password"
              className={`input pl-9 pr-10 ${errors.confirmPassword ? 'input-error' : ''}`}
              id="register-confirm-password"
              {...register('confirmPassword')}
            />
            <button type="button" onClick={() => setShowConfirm(!showConfirm)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-200/50">
              {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.confirmPassword && <p className="text-danger-400 text-xs">{errors.confirmPassword.message}</p>}
        </div>

        <Button
          type="submit"
          loading={loading}
          icon={<UserPlus size={16} />}
          className="w-full btn-lg"
          id="register-submit-btn"
        >
          Create Account
        </Button>

        <p className="text-xs text-dark-100/30 text-center">
          By creating an account, you agree to our{' '}
          <a href="#" className="text-primary-400">Terms of Service</a> and{' '}
          <a href="#" className="text-primary-400">Privacy Policy</a>.
        </p>
      </form>

      <p className="text-center text-dark-100/50 text-sm mt-6">
        Already have an account?{' '}
        <Link to="/login" className="text-primary-400 font-semibold">Sign in</Link>
      </p>
    </div>
  )
}
