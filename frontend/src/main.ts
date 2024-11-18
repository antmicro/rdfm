/*
 * Copyright (c) 2024 Antmicro <www.antmicro.com>
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import './assets/main.css';

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import ToastPlugin from 'vue-toast-notification';

if (import.meta.env.VITE_CUSTOM_FAVICON) {
    const link = document.getElementById('favicon') as HTMLLinkElement;
    link.href = import.meta.env.VITE_CUSTOM_FAVICON;
}

if (import.meta.env.VITE_CUSTOM_STYLESHEET) {
    const head = document.querySelector('head');
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.setAttribute('crossorigin', 'true');
    link.href = import.meta.env.VITE_CUSTOM_STYLESHEET;
    head!.appendChild(link);
}

const app = createApp(App);

app.use(router);
app.use(ToastPlugin);
app.mount('#app');
