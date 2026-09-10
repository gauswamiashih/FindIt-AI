/**
 * Auth API functions
 */

import api from './api'

export const authService = {
  register:            (data) => api.post('/auth/register', data),
  login:               (data) => api.post('/auth/login', data),
  logout:              ()     => api.post('/auth/logout'),
  verifyEmail:         (token) => api.get(`/auth/verify-email/${token}`),
  resendVerification:  (email) => api.post('/auth/resend-verification', { email }),
  forgotPassword:      (email) => api.post('/auth/forgot-password', { email }),
  resetPassword:       (token, password) => api.post(`/auth/reset-password/${token}`, { password }),
  refreshToken:        (refreshToken) => api.post('/auth/refresh-token', { refreshToken }),
  getMe:               () => api.get('/auth/me'),
  changePassword:      (data) => api.put('/auth/change-password', data),
}

export const userService = {
  getProfile:    (id) => api.get(id ? `/users/${id}` : '/users/me'),
  updateProfile: (data) => api.put('/users/me', data),
  updateSettings:(data) => api.put('/users/me/settings', data),
  getActivity:   (id) => api.get(id ? `/users/${id}/activity` : '/users/me/activity'),
}

export const lostItemService = {
  create: (data) => {
    if (data instanceof FormData) {
      if (!data.has('item_type')) data.append('item_type', 'lost')
      return api.post('/items/form', data)
    }
    return api.post('/items', { ...data, item_type: 'lost' })
  },
  getAll: (params) => api.get('/items', { params: { ...params, type: 'lost' } }),
  getById: (id) => api.get(`/items/${id}`),
  update: (id, data) => api.patch(`/items/${id}`, data),
  delete: (id) => api.delete(`/items/${id}`),
  getMine: (params) => api.get('/items', { params: { ...params, type: 'lost', my: true } }),
  deleteImage: (id, publicId) => api.delete(`/items/${id}/images/${encodeURIComponent(publicId)}`),
}

export const foundItemService = {
  create: (data) => {
    if (data instanceof FormData) {
      if (!data.has('item_type')) data.append('item_type', 'found')
      return api.post('/items/form', data)
    }
    return api.post('/items', { ...data, item_type: 'found' })
  },
  getAll: (params) => api.get('/items', { params: { ...params, type: 'found' } }),
  getById: (id) => api.get(`/items/${id}`),
  update: (id, data) => api.patch(`/items/${id}`, data),
  delete: (id) => api.delete(`/items/${id}`),
  getMine: (params) => api.get('/items', { params: { ...params, type: 'found', my: true } }),
}


export const matchService = {
  getAll:   (params) => api.get('/matches', { params }),
  getById:  (id) => api.get(`/matches/${id}`),
  confirm:  (id, data) => api.post(`/matches/${id}/confirm`, data),
  reject:   (id, data) => api.post(`/matches/${id}/reject`, data),
  analyze:  (itemId, params) => api.post(`/matches/item/${itemId}/analyze`, null, { params }),
}


export const chatService = {
  getChats:      ()         => api.get('/chats'),
  getMessages:   (chatId, params) => api.get(`/chats/${chatId}/messages`, { params }),
  sendMessage:   (chatId, data) => {
    const payload = typeof data === 'string' ? { text: data } : { text: data.text || data.content || '' }
    return api.post(`/chats/${chatId}/messages`, payload)
  },
  deleteMessage: (chatId, messageId) => api.delete(`/chats/${chatId}/messages/${messageId}`),
}

export const notificationService = {
  getAll:         (params) => api.get('/notifications', { params }),
  markRead:       (id) => api.patch(`/notifications/${id}/read`),
  getUnreadCount: () => api.get('/notifications/unread-count'),
}

export const searchService = {
  search:      (params) => api.get('/items/search', { params }),
  suggestions: (q) => api.get('/items/search', { params: { q, limit: 5 } }),
}

export const adminService = {
  getStats:         () => api.get('/admin/stats'),
  getUsers:         (params) => api.get('/admin/users', { params }),
  updateUserStatus: (id, data) => api.patch(`/admin/users/${id}/status`, data),
  banUser:          (id, data) => api.patch(`/admin/users/${id}/status`, { ...data, is_verified: false }),
  unbanUser:        (id) => api.patch(`/admin/users/${id}/status`, { is_verified: true }),
  promoteUser:      (id) => api.patch(`/admin/users/${id}/status`, { role: 'admin' }),
  getItems:         (params) => api.get('/admin/items', { params }),
  updateItemStatus: (id, data) => api.patch(`/admin/items/${id}/status`, data),
}
