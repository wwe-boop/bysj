import { defineStore } from 'pinia'
import type { Notification } from '@/types'

interface AppState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  language: 'zh-CN' | 'en-US'
  notifications: Notification[]
  loading: boolean
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    theme: 'light',
    sidebarCollapsed: false,
    language: 'zh-CN',
    notifications: [],
    loading: false
  }),

  getters: {
    isDark: (state) => state.theme === 'dark',
    
    unreadNotifications: (state) => 
      state.notifications.filter(n => !n.read),
    
    notificationCount: (state) => 
      state.notifications.filter(n => !n.read).length
  },

  actions: {
    setTheme(theme: 'light' | 'dark') {
      this.theme = theme
      document.documentElement.classList.toggle('dark', theme === 'dark')
      localStorage.setItem('theme', theme)
    },

    toggleTheme() {
      this.setTheme(this.theme === 'light' ? 'dark' : 'light')
    },

    setSidebarCollapsed(collapsed: boolean) {
      this.sidebarCollapsed = collapsed
      localStorage.setItem('sidebarCollapsed', String(collapsed))
    },

    toggleSidebar() {
      this.setSidebarCollapsed(!this.sidebarCollapsed)
    },

    setLanguage(language: 'zh-CN' | 'en-US') {
      this.language = language
      localStorage.setItem('language', language)
    },

    setLoading(loading: boolean) {
      this.loading = loading
    },

    addNotification(notification: Omit<Notification, 'id' | 'timestamp'>) {
      const id = Date.now().toString()
      const timestamp = Date.now()
      
      this.notifications.unshift({
        id,
        timestamp,
        read: false,
        ...notification
      })

      // 限制通知数量
      if (this.notifications.length > 100) {
        this.notifications = this.notifications.slice(0, 100)
      }
    },

    markNotificationRead(id: string) {
      const notification = this.notifications.find(n => n.id === id)
      if (notification) {
        notification.read = true
      }
    },

    markAllNotificationsRead() {
      this.notifications.forEach(n => n.read = true)
    },

    removeNotification(id: string) {
      const index = this.notifications.findIndex(n => n.id === id)
      if (index > -1) {
        this.notifications.splice(index, 1)
      }
    },

    clearNotifications() {
      this.notifications = []
    },

    // 初始化应用状态
    initializeApp() {
      // 从localStorage恢复设置
      const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
      if (savedTheme) {
        this.setTheme(savedTheme)
      }

      const savedSidebarCollapsed = localStorage.getItem('sidebarCollapsed')
      if (savedSidebarCollapsed) {
        this.setSidebarCollapsed(savedSidebarCollapsed === 'true')
      }

      const savedLanguage = localStorage.getItem('language') as 'zh-CN' | 'en-US' | null
      if (savedLanguage) {
        this.setLanguage(savedLanguage)
      }
    }
  }
})
