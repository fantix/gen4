import Vue from 'vue'
import VueRouter from 'vue-router'
import Home from '../views/Home.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home,
  },
  {
    path: '/buckets',
    name: 'buckets',
    component: () => import('../views/Buckets.vue')
  },
  {
    path: '/files',
    name: 'files',
    component: () => import('../views/Files.vue')
  },
  {
    path: '/docs',
    name: 'docs',
    component: () => import('../views/ApiDocs.vue')
  },
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

export default router
