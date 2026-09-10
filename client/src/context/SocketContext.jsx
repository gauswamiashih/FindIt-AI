/**
 * Socket Context
 * Manages WebSocket connection to FastAPI real-time chat backend
 */

import { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react'
import { useAuth } from './AuthContext'

const SocketContext = createContext(null)

export const SocketProvider = ({ children }) => {
  const { user, isAuthenticated } = useAuth()
  const [activeSocket, setActiveSocket] = useState(null)
  const [onlineUsers, setOnlineUsers] = useState([])
  const wsRef = useRef(null)

  const connectToChat = useCallback((chatId, onMessageReceived) => {
    if (!isAuthenticated || !chatId) return null
    const token = localStorage.getItem('accessToken')
    if (!token) return null

    if (wsRef.current) {
      wsRef.current.close()
    }

    const envWsUrl = import.meta.env.VITE_WS_URL
    let wsBaseUrl = envWsUrl
    if (!wsBaseUrl) {
      const loc = window.location
      const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = loc.host || 'localhost:8000'
      wsBaseUrl = `${protocol}//${host}`
    }

    const wsUrl = `${wsBaseUrl.replace(/\/$/, '')}/api/v1/chats/ws/${chatId}?token=${encodeURIComponent(token)}`
    
    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('🔌 WebSocket connected to chat:', chatId)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (onMessageReceived) {
            onMessageReceived(data)
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onerror = (err) => {
        console.warn('WebSocket error:', err)
      }

      ws.onclose = () => {
        console.log('🔌 WebSocket closed for chat:', chatId)
      }

      wsRef.current = ws
      setActiveSocket(ws)
      return ws
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      return null
    }
  }, [isAuthenticated])

  const disconnectSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
      setActiveSocket(null)
    }
  }, [])

  const sendMessage = useCallback((text) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ text }))
      return true
    }
    return false
  }, [])

  // Dummy fallback helpers for backwards compatibility
  const joinChat = useCallback((chatId) => {}, [])
  const leaveChat = useCallback((chatId) => disconnectSocket(), [disconnectSocket])
  const sendTyping = useCallback((chatId, isTyping) => {}, [])

  useEffect(() => {
    return () => {
      disconnectSocket()
    }
  }, [disconnectSocket])

  return (
    <SocketContext.Provider value={{
      socket: activeSocket,
      onlineUsers,
      connectToChat,
      disconnectSocket,
      sendMessage,
      joinChat,
      leaveChat,
      sendTyping
    }}>
      {children}
    </SocketContext.Provider>
  )
}

export const useSocket = () => {
  const ctx = useContext(SocketContext)
  if (!ctx) throw new Error('useSocket must be used within SocketProvider')
  return ctx
}
