/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            // This is needed for when the built application
            // is served from a subdirectory
            path: '/:catchAll(.*)',
            name: 'home',
            component: HomeView,
        },
    ],
});

export default router;
