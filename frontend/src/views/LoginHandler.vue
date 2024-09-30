<template>
    <p>Logging in</p>
</template>

<script lang="ts">
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
            throw new Error('No token found. Make sure you are logged in.');
        }

        localStorage.setItem('access_token', token);
        this.router.push('/');
    },
};
</script>
