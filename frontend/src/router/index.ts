/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import LoginHandler from '../views/LoginHandler.vue';
import LogoutHandler from '../views/LogoutHandler.vue';

// Backend endpoint on which frontend app is server has to be
// equal to this variable. If the frontend app is served by the
// backend, its URL is prefixed with this value and router
// has to be aware of that.
export const BASE_URL = import.meta.env.VITE_RDFM_BACKEND === 'true' ? '/api/static/frontend' : '';

const routes: RouteRecordRaw[] = [
    {
        // This is needed for when the built application
        // is served from a subdirectory
        path: '/',
        name: 'home',
        component: HomeView,
    },
    {
        path: '/auth_data',
        name: 'login',
        component: LoginHandler,
    },
    {
        path: '/logout',
        name: 'logout',
        component: LogoutHandler,
    },
];

const router = createRouter({
    history: createWebHistory(BASE_URL),
    routes: routes,
});

export default router;
