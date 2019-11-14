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
          <template v-if="bucket !== null">
            <v-divider></v-divider>
            <v-toolbar color="white" dense flat>
              <v-btn @click="goUp" depressed small>
                <v-img src="../assets/go-parent-folder.svg"></v-img>
              </v-btn>
            </v-toolbar>
            <v-data-table
                :headers="headers"
                :items="files"
                :items-per-page="15"
                :loading="listLoading"
                @click:row="clicked"
                class="gen3-table"
                dense
                item-key="name"
                no-data-text="This directory is empty."
                single-select
                v-model="selected">
              <template v-slot:item.dir="{ item }">
                <v-img :src="mimeIcon(item.dir ? 'inode/directory' : item.mime)"
                       width="20"></v-img>
              </template>
            </v-data-table>
          </template>
        </v-card>
      </v-col>
      <v-col class="pl-4">
        <v-card :loading="detailLoading" class="px-8 py-5" v-if="detail">
          <v-card-title>Detail</v-card-title>
          <v-divider></v-divider>
          <v-img :src="mimeIcon(detail.mime)" class="mx-12"></v-img>
          <v-text-field :value="detail.name" label="Name" readonly></v-text-field>
          <v-text-field :value="detail.size" label="Size" readonly
                        v-if="!detail.dir"></v-text-field>
          <v-text-field :value="detail.files.length"
                        label="Number of files/dirs included" readonly
                        v-if="detail.dir"></v-text-field>
          <v-text-field :value="detail.type" label="Type" readonly></v-text-field>
          <v-textarea :value="detail.preview" auto-grow class="overline" label="Preview"
                      readonly v-if="detail.preview"></v-textarea>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
    import axios from 'axios'

    export default {
        name: "Files",
        clickTime: 0,
        detailCancelToken: null,
        data: () => ({
            bucket: null,
            buckets: [],
            files: [],
            path: [],
            selected: [],
            detail: null,
            detailLoading: false,
            listLoading: false,
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
                this.listLoading = true
                try {
                    let resp = await this.$axios.get(`/api/objects/buckets/${val}/?recursive=false`)
                    this.files = resp.data.files
                } catch (e) {
                }
                this.listLoading = false
            },
        },
        methods: {
            async clicked(row) {
                let now = Date.now()
                if (this.selected[0] === row && now - this.clickTime < 500) {
                    this.clickTime = 0
                    if (row.dir) {
                        this.path.push(row.name)
                        this.listLoading = true
                        try {
                            let resp = await this.$axios.get(`/api/objects/buckets/${this.bucket}/${this.path.join('/')}?recursive=false`)
                            this.files = resp.data.files
                            this.detail = null
                        } catch (e) {
                            this.path.pop()
                        }
                        this.listLoading = false
                    }
                } else {
                    this.clickTime = now
                    this.selected = [row]
                    this.detailLoading = true
                    if (this.detailCancelToken !== null) {
                        try {
                            this.detailCancelToken.cancel('Operation canceled by the user.')
                        } catch (e) {
                        }
                        this.detailCancelToken = axios.CancelToken.source()
                    }
                    try {
                        let resp = await this.$axios.get(
                            `/api/objects/buckets/${this.bucket}/${this.path.join('/')}` +
                            `/${row.name}?recursive=false`,
                            {cancelToken: this.detailCancelToken.token},
                        )
                        this.detail = resp.data
                    } catch (e) {
                        this.detail = null
                    }
                    this.detailLoading = false
                }
            },
            async goUp() {
                this.selected = []
                if (this.path) {
                    let row = this.path.pop()
                    this.listLoading = true
                    try {
                        let resp = await this.$axios.get(`/api/objects/buckets/${this.bucket}/${this.path.join('/')}?recursive=false`)
                        this.files = resp.data.files
                        this.detail = null
                    } catch (e) {
                        this.path.push(row)
                    }
                    this.listLoading = false
                }
            },
            mimeIcon(mime) {
                try {
                    return require('../assets/mimetypes/' + mime.replace('/', '-') + '.svg')
                } catch (e) {
                    return require('../assets/mimetypes/unknown.svg')
                }
            },
        }
    }
</script>

<style>
  .gen3-table.v-data-table tbody tr.v-data-table__selected {
    background-color: var(--v-accent2-lighten3);
  }

  .gen3-table.v-data-table tbody tr:hover:not(.v-data-table__expanded__content) {
    background-color: var(--v-secondary-lighten3);
  }

  textarea {
    font-family: monospace;
  }
</style>