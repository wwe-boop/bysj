import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: {
          title: '仪表板',
          icon: 'DataBoard'
        }
      },
      {
        path: '/simulation',
        name: 'Simulation',
        component: () => import('@/views/Simulation.vue'),
        meta: {
          title: '仿真控制',
          icon: 'VideoPlay'
        }
      },
      {
        path: '/visualization',
        name: 'Visualization',
        component: () => import('@/views/Visualization.vue'),
        meta: {
          title: '可视化',
          icon: 'TrendCharts'
        }
      },
      {
        path: '/network',
        name: 'Network',
        component: () => import('@/views/Network.vue'),
        meta: {
          title: '网络拓扑',
          icon: 'Share'
        }
      },
      {
        path: '/admission',
        name: 'Admission',
        component: () => import('@/views/Admission.vue'),
        meta: {
          title: '准入控制',
          icon: 'Key'
        }
      },
      {
        path: '/positioning',
        name: 'Positioning',
        component: () => import('@/views/Positioning.vue'),
        meta: {
          title: '定位服务',
          icon: 'Location'
        }
      },
      {
        path: '/scenarios',
        name: 'Scenarios',
        component: () => import('@/views/Scenarios.vue'),
        meta: {
          title: '场景管理',
          icon: 'Setting'
        }
      },
      {
        path: '/statistics',
        name: 'Statistics',
        component: () => import('@/views/Statistics.vue'),
        meta: {
          title: '统计分析',
          icon: 'DataAnalysis'
        }
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      title: '登录',
      hideInMenu: true
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面不存在',
      hideInMenu: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - LEO卫星网络仿真系统`
  }
  
  next()
})

export default router
