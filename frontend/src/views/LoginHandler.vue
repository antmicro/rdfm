<template>
    <p>Logging in</p>
</template>

<script lang="ts">
import { LOGIN_PATH } from '@/common/utils';
import { useRoute, useRouter } from 'vue-router';

export default {
    setup() {
        return {
            route: useRoute(),
            router: useRouter(),
        };
    },
    mounted() {
        const params = new URLSearchParams(this.route.hash);
        const token = params.get('access_token');
        if (!token) {
            console.error('No token found. Make sure you are logged in.');
            window.location.href = LOGIN_PATH;
            return;
        }

        localStorage.setItem('access_token', token);

        const currentPath = localStorage.getItem('current_path') ?? '/';
        const resolved = this.router.resolve(currentPath);
        if (resolved.matched.length === 0) {
            this.router.push('/');
        } else {
            this.router.push(currentPath);
        }
    },
};
</script>
