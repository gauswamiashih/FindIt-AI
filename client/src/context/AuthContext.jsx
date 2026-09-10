/**
 * Auth Context
 * Supabase Auth + FastAPI Backend Synchronization
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { supabase } from '../utils/supabase'
import { authService } from '../services'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [user, setUser]       = useState(null)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  // ─── Sync Supabase Session with FastAPI Backend ─────────────────────────────
  const syncUserWithBackend = useCallback(async (currentSession) => {
    if (!currentSession?.access_token) {
      setUser(null)
      setSession(null)
      localStorage.removeItem('accessToken')
      localStorage.removeItem('user')
      setLoading(false)
      return
    }

    try {
      localStorage.setItem('accessToken', currentSession.access_token)
      setSession(currentSession)

      // Fetch verified user model from FastAPI backend
      const { data } = await authService.getMe()
      const appUser = data.data || data
      setUser(appUser)
      localStorage.setItem('user', JSON.stringify(appUser))
    } catch (error) {
      console.error('Failed to sync authenticated user with FastAPI:', error)
      // Token invalid or backend unreachable
      setUser(null)
      setSession(null)
      localStorage.removeItem('accessToken')
      localStorage.removeItem('user')
    } finally {
      setLoading(false)
    }
  }, [])

  // ─── Initialize Supabase Auth & Session listener ────────────────────────────
  useEffect(() => {
    // 1. Get initial session
    supabase.auth.getSession().then(({ data: { session: initSession } }) => {
      syncUserWithBackend(initSession)
    })

    // 2. Listen for auth changes (Google OAuth callback, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, currentSession) => {
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          await syncUserWithBackend(currentSession)
        } else if (event === 'SIGNED_OUT') {
          setUser(null)
          setSession(null)
          localStorage.clear()
          setLoading(false)
        }
      }
    )

    return () => {
      subscription?.unsubscribe()
    }
  }, [syncUserWithBackend])

  // ─── Google Login ───────────────────────────────────────────────────────────
  const loginWithGoogle = useCallback(async () => {
    setLoading(true)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    })
    if (error) {
      setLoading(false)
      throw error
    }
  }, [])

  // ─── Email/Password Login ───────────────────────────────────────────────────
  const login = useCallback(async (credentials) => {
    setLoading(true)
    try {
      // Authenticate via Supabase Auth
      const { data, error } = await supabase.auth.signInWithPassword({
        email: credentials.email,
        password: credentials.password,
      })
      if (error) throw error

      if (data.session) {
        await syncUserWithBackend(data.session)
      }
      return data.user
    } catch (err) {
      setLoading(false)
      throw err
    }
  }, [syncUserWithBackend])

  // ─── Register with Email ─────────────────────────────────────────────────────
  const register = useCallback(async (credentials) => {
    setLoading(true)
    try {
      const { data, error } = await supabase.auth.signUp({
        email: credentials.email,
        password: credentials.password,
        options: {
          data: {
            full_name: credentials.name,
          },
        },
      })
      if (error) throw error

      if (data.session) {
        await syncUserWithBackend(data.session)
      }
      return data.user
    } catch (err) {
      setLoading(false)
      throw err
    }
  }, [syncUserWithBackend])

  // ─── Logout ──────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    setLoading(true)
    try {
      await supabase.auth.signOut()
      await authService.logout().catch(() => {})
    } finally {
      setUser(null)
      setSession(null)
      localStorage.clear()
      setLoading(false)
    }
  }, [])

  // ─── Update User Profile ─────────────────────────────────────────────────────
  const updateUser = useCallback((updatedUser) => {
    setUser(updatedUser)
    localStorage.setItem('user', JSON.stringify(updatedUser))
  }, [])

  const isAdmin = user?.role === 'admin'
  const isAuthenticated = !!user

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isAuthenticated,
        isAdmin,
        loginWithGoogle,
        login,
        register,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
