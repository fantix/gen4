<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-container fluid ma-0 pa-0>
    <v-row dense>
      <v-col cols="8">
        <v-card class="px-8 py-5">
          <v-data-table
              :headers="headers"
              :items="buckets"
              :items-per-page="5">
            <template v-slot:top>
              <v-toolbar color="white" flat>
                <v-toolbar-title>Buckets</v-toolbar-title>
                <v-spacer></v-spacer>
                <v-dialog max-width="500px" v-model="dialog">
                  <template v-slot:activator="{ on }">
                    <v-btn color="secondary" v-on="on">
                      Add Bucket
                    </v-btn>
                  </template>
                  <v-card>
                    <v-card-title>
                      <span class="headline">{{ formTitle }}</span>
                    </v-card-title>

                    <v-card-text>
                      <v-container>
                        <v-row>
                          <v-col cols="12" md="5" sm="4">
                            <v-select
                                :error="errors.driver !== null"
                                :error-messages="errors.driver"
                                :items="Object.keys(drivers)"
                                :prepend-icon="icons[editedItem.driver]"
                                :readonly="editedIndex !== -1"
                                label="Bucket Driver"
                                v-model="editedItem.driver">
                            </v-select>
                          </v-col>
                          <v-col cols="12" md="7" sm="4">
                            <v-text-field
                                :error="errors.name !== null"
                                :error-messages="errors.name"
                                :readonly="editedIndex !== -1"
                                label="Bucket Name"
                                v-model="editedItem.name"></v-text-field>
                          </v-col>
                          <v-col cols="12" md="12" sm="6" :key="field.name"
                                 v-for="field in editedFields">
                            <v-text-field
                                :error="errors[field.name] !== null"
                                :error-messages="errors[field.name]"
                                :label="field.title"
                                v-model="editedItem.settings[field.name]"></v-text-field>
                          </v-col>
                        </v-row>
                      </v-container>
                    </v-card-text>

                    <v-card-actions>
                      <v-spacer></v-spacer>
                      <v-btn :disabled="saving" @click="close" color="#aaa darken-1"
                             text>Cancel
                      </v-btn>
                      <v-btn :loading="saving" @click="save" color="primary darken-1"
                             text>Save
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>
              </v-toolbar>
            </template>
            <template v-slot:item.driver="{ item }">
              <v-tooltip bottom>
                <template v-slot:activator="{ on }">
                  <span
                      :style="{color: item.installed ? 'inherit' : '#ccc'}"
                      v-on="on">
                      <v-icon
                          :color="item.installed ? 'inherit' : '#ccc'">
                          {{icons[item.driver] || 'mdi-cloud-question'}}
                      </v-icon>
                      {{item.driver}}
                  </span>
                </template>
                <span>{{Object.assign({desc: 'Unknown bucket driver.'}, drivers[item.driver]).desc}}</span>
              </v-tooltip>
            </template>
            <template v-slot:item.enabled="{ item }">
              <v-switch :disabled="!item.installed" :loading="item.loading"
                        :readonly="item.loading"
                        @change="enabled => toggleEnabled(item, enabled)"
                        v-model="item.enabled"></v-switch>
            </template>
            <template v-slot:item.action="{ item }">
              <v-icon @click="editItem(item)">
                mdi-pencil
              </v-icon>
            </template>
            <template v-slot:no-data>
              no data
            </template>

          </v-data-table>
        </v-card>
      </v-col>
      <v-col class="pl-4">
        <v-card class="px-8">
          <v-card-title>Installed Bucket Drivers</v-card-title>
          <v-divider></v-divider>
          <v-list-item :key="name" two-line v-for="(driver, name) in drivers">
            <v-list-item-avatar>
              <v-icon>{{icons[name]}}</v-icon>
            </v-list-item-avatar>
            <v-list-item-content>
              <v-list-item-title>{{name}}</v-list-item-title>
              <v-list-item-subtitle>{{driver.desc}}
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
        name: "Buckets",
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
                {text: 'Driver', value: 'driver', width: 120},
                {text: 'Enabled', value: 'enabled', width: 120},
                {text: 'Actions', value: 'action', sortable: false, width: 120},
            ],
            buckets: [],
            drivers: {},
            drivers: [],
            dialog: false,
            editedIndex: -1,
            editedItem: {
                name: '',
                driver: '',
                settings: {},
            },
            errors: {
                name: null,
                driver: null,
            },
            defaultItem: {
                name: '',
                driver: '',
                settings: {},
            },
            saving: false,
        }),
        async mounted() {
            this.reload()
            this.drivers = (await this.$axios.get('/api/objects/drivers')).data
        },
        computed: {
            formTitle() {
                return this.editedIndex === -1 ? 'Add Bucket' : 'Edit Bucket'
            },
            editedFields() {
                let p = this.drivers[this.editedItem.driver]
                if (!p) return []
                let rv = []
                for (let field of Object.keys(p.settings.properties)) {
                    let values = p.settings.properties[field]
                    rv.push({
                        name: field,
                        title: values.title,
                        type: values.type,
                    })
                }
                return rv
            }
        },
        watch: {
            'editedItem.driver'(val) {
                let p = this.drivers[val]
                if (!p) return
                for (let field of Object.keys(p.settings.properties)) {
                    this.errors[field] = null
                }
            }
        },
        methods: {
            async reload() {
                let buckets = (await this.$axios.get('/api/objects/buckets')).data
                for (let i in buckets) {
                    if (!buckets[i].installed) {
                        buckets[i].enabled = false
                    }
                    buckets[i].loading = false
                }
                this.buckets = buckets
            },
            async toggleEnabled(item, enabled) {
                item.loading = true
                try {
                    await this.$axios.put(item.href, {enabled: enabled})
                } catch (e) {
                    await sleep(1)
                    item.enabled = !enabled
                }
                item.loading = false
            },
            async editItem(item) {
                let data = (await this.$axios.get(item.href)).data
                this.editedIndex = this.buckets.indexOf(item)
                this.editedItem = Object.assign({}, data)
                this.dialog = true
            },
            async close() {
                this.dialog = false
                await sleep(0.3)
                this.editedItem = Object.assign({}, this.defaultItem)
                this.editedIndex = -1
            },
            async save() {
                this.saving = true
                for (let key of Object.keys(this.errors)) {
                    this.errors[key] = null
                }
                try {
                    if (this.editedIndex === -1) {
                        let resp = await this.$axios.post('/api/objects/buckets', {
                            name: this.editedItem.name,
                            driver: this.editedItem.driver,
                            settings: this.editedItem.settings,
                        })
                        resp = await this.$axios.get(resp.data.href)
                        this.buckets.push(resp.data)
                    } else {
                        let href = this.buckets[this.editedIndex].href
                        await this.$axios.put(href, {
                            settings: this.editedItem.settings,
                        })
                        let resp = await this.$axios.get(href)
                        Object.assign(this.buckets, resp.data)
                    }
                    this.close()
                } catch (e) {
                    for (let err of e.response.data.detail) {
                        this.errors[err.loc[err.loc.length - 1]] = err.msg
                    }
                }
                this.saving = false
            },
        }
    }
</script>

<style scoped>

</style>