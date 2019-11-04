<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
    <v-container fluid ma-0 pa-0>
        <v-row dense>
            <v-col cols="8">
                <v-card class="px-8 pb-8">
                    <v-card-title>Buckets</v-card-title>
                    <v-divider></v-divider>
                    <v-data-table
                            :headers="headers"
                            :items="buckets"
                            :items-per-page="5">
                        <template v-slot:item.provider="{ item }">
                            <v-tooltip bottom>
                                <template v-slot:activator="{ on }">
                                    <span v-on="on"
                                          :style="{color: (item.installed && item.enabled) ? 'inherit' : '#ccc'}">
                                        <v-icon :color="(item.installed && item.enabled) ? 'inherit' : '#ccc'">
                                            {{icons[item.provider] || 'mdi-cloud-question'}}
                                        </v-icon>
                                        {{item.provider}}
                                    </span>
                                </template>
                                <span>{{providers[item.provider] || 'Unknown bucket driver.'}}</span>
                            </v-tooltip>
                        </template>
                        <template v-slot:item.enabled="{ item }">
                            <v-switch v-model="item.enabled" :disabled="!item.installed"
                                      :readonly="item.loading" :loading="item.loading"
                                      @change="enabled => toggleEnabled(item, enabled)"></v-switch>
                        </template>
                    </v-data-table>
                </v-card>
            </v-col>
            <v-col class="pl-4">
                <v-card class="px-8">
                    <v-card-title>Installed Bucket Drivers</v-card-title>
                    <v-divider></v-divider>
                    <v-list-item two-line v-for="(desc, provider) in providers">
                        <v-list-item-avatar>
                            <v-icon>{{icons[provider]}}</v-icon>
                        </v-list-item-avatar>
                        <v-list-item-content>
                            <v-list-item-title>{{provider}}</v-list-item-title>
                            <v-list-item-subtitle>{{desc}}
                            </v-list-item-subtitle>
                        </v-list-item-content>
                    </v-list-item>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
    function sleep(s) {
        return new Promise(resolve => setTimeout(resolve, s * 1000));
    }

    export default {
        name: "Bucket",
        data: () => ({
            icons: {
                fs: 'mdi-harddisk',
                s3: 'mdi-aws',
                gs: 'mdi-google',
                cs: 'mdi-server-security',
                ftp: 'mdi-server-network',
            },
            headers: [
                {text: 'Name', value: 'name'},
                {text: 'Driver', value: 'provider'},
                {text: 'Enabled', value: 'enabled'},
            ],
            buckets: [],
            providers: {},
        }),
        async mounted() {
            let providers = this.$axios.get('/api/objects/providers')
            let buckets = this.$axios.get('/api/objects/buckets')
            buckets = (await buckets).data
            for (let i in buckets) {
                if (!buckets[i].installed) {
                    buckets[i].enabled = false
                }
                buckets[i].loading = false
            }
            this.buckets = buckets
            this.providers = (await providers).data
        },
        methods: {
            async toggleEnabled(item, enabled) {
                item.loading = true
                try {
                    await this.$axios.put(item.href, {enabled: enabled})
                } catch (e) {
                    await sleep(1)
                    item.enabled = !enabled
                }
                item.loading = false
            }
        }
    }
</script>

<style scoped>

</style>