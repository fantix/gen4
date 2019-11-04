<template>
    <v-card>
        <iframe ref="swagger" class="swagger" src="/api/docs" height="300px"></iframe>
    </v-card>
</template>

<style scoped>
    .swagger {
        width: 100%;
        border: none;
    }
</style>

<script>
    export default {
        mounted() {
            document.addEventListener('swagger-resize', this.resize)
        },
        beforeDestroy() {
            document.removeEventListener('swagger-resize', this.resize)
        },
        methods: {
            resize() {
                this.$refs.swagger.height = this.$refs.swagger.contentWindow.document.body.scrollHeight + 10
            }
        }
    }
</script>
