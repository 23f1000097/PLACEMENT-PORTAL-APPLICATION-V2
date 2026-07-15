import { createRouter, createWebHistory } from 'vue-router'
import AuthPage from '../views/AuthPage.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import CompanyDashboard from '../views/CompanyDashboard.vue'
import StudentDashboard from '../views/StudentDashboard.vue'
import { usePpaStore } from '../stores/ppa'

const routes = [
  { path: '/', name: 'Auth', component: AuthPage },
  { path: '/admin', name: 'AdminDashboard', component: AdminDashboard, meta: { role: 'admin' } },
  { path: '/company', name: 'CompanyDashboard', component: CompanyDashboard, meta: { role: 'company' } },
  { path: '/student', name: 'StudentDashboard', component: StudentDashboard, meta: { role: 'student' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const store = usePpaStore()

  if (!to.meta?.role) {
    return true
  }
  if (!store.isLoggedIn) {
    return { path: '/' }
  }
  if (store.user?.role !== to.meta.role) {
    return { path: `/${store.user.role}` }
  }
  return true
})

export default router
