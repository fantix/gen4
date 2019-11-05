<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-container fluid ma-0 pa-0>
    <v-row dense>
      <v-col cols="8">
        <v-card class="px-8 py-5">
          <v-toolbar color="white" flat>
            <v-toolbar-title>Bucket File Browser</v-toolbar-title>
            <v-spacer/>
            <v-combobox :items="buckets" dense flat hide-details label="Choose Bucket"
                        outlined solo v-model="bucket">
            </v-combobox>
          </v-toolbar>
          <v-divider></v-divider>
          <v-toolbar color="white" flat dense>
            <v-btn @click="goUp" depressed small><v-icon>mdi-arrow-up-bold</v-icon></v-btn>
          </v-toolbar>
          <v-data-table
              :headers="headers"
              :items="files"
              :items-per-page="15"
              @click:row="clicked"
              dense>

            <template v-slot:item.dir="{ item }">
              <v-icon>{{ item.dir ? 'mdi-folder-open' : 'mdi-file-outline'}}</v-icon>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
      <v-col class="pl-4">
        <v-card class="px-8 py-5">
          <v-card-title>Details</v-card-title>
          <v-divider></v-divider>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
    export default {
        name: "Files",
        data: () => ({
            bucket: null,
            buckets: [],
            files: [],
            path: [],
            headers: [
                {text: '', value: 'dir', width: 1},
                {text: 'Name', value: 'name'},
                {text: 'Size', value: 'size'},
            ],
        }),
        async mounted() {
            this.buckets = (await this.$axios.get('/api/objects/buckets')).data.map(b => b.name)
        },
        watch: {
            async bucket(val) {
                this.path = []
                let resp = await this.$axios.get(`/api/objects/buckets/${val}/?recursive=false`)
                this.files = resp.data
            },
        },
        methods: {
            async clicked(row) {
                if (row.dir) {
                    this.path.push(row.name)
                    try {
                        let resp = await this.$axios.get(`/api/objects/buckets/${this.bucket}/${this.path.join('/')}?recursive=false`)
                        this.files = resp.data
                    } catch (e) {
                        this.path.pop()
                    }
                }
            },
            async goUp() {
                if (this.path) {
                    let row = this.path.pop()
                    try {
                        let resp = await this.$axios.get(`/api/objects/buckets/${this.bucket}/${this.path.join('/')}?recursive=false`)
                        this.files = resp.data
                    } catch (e) {
                        this.path.push(row)
                    }
                }
            },
        }
    }
</script>

<style scoped>

</style>