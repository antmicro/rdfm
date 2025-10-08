/*
 * Copyright (c) 2024-2025 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import HomeView, { ActiveTab, SECTIONS } from '../views/HomeView.vue';
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
        redirect: '/groups',
    },
    ...SECTIONS.map((activeTab) => ({
        path: `/${activeTab}`,
        name: activeTab,
        component: HomeView,
        props: { activeTab },
    })),
    {
        path: '/devices/:id',
        name: ActiveTab.Device,
        component: HomeView,
        props: { activeTab: ActiveTab.Device },
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

router.beforeEach((to, from, next) => {
    if (!to.fullPath.startsWith('/auth_data')) {
        localStorage.setItem('current_path', to.fullPath);
    }
    next();
});

export default router;
