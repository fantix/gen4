<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title class="headline text-uppercase">
        <span class="mr-2">Gen3</span>
        <span class="font-weight-light">Data Commons</span>
      </v-toolbar-title>
      <v-btn rounded color="grey" dark x-small class="ml-3">{{ version }}</v-btn>
      <v-spacer></v-spacer>
      <router-link to="/" v-slot="href">
        <v-btn text :href="href.href">
          <v-icon>mdi-home</v-icon>
          <span class="ml-1">Home</span>
        </v-btn>
      </router-link>
      <router-link to="/docs" v-slot="href">
        <v-btn text :href="href.href">
          <v-icon>mdi-code-tags</v-icon>
          <span class="ml-1">API Docs</span>
        </v-btn>
      </router-link>
      <router-link to="/about" v-slot="href">
        <v-btn text :href="href.href">
          <v-icon>mdi-information</v-icon>
          <span class="ml-1">About</span>
        </v-btn>
      </router-link>
      <v-btn text href="https://gen3.org/" target="_blank">
        <span class="mr-1">Website</span>
        <v-icon>mdi-open-in-new</v-icon>
      </v-btn>
    </v-app-bar>

    <v-content>
      <router-view/>
    </v-content>
  </v-app>
</template>

<style lang="scss">
  #app {
    font-family: 'Source Sans Pro', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
  }
</style>

<script>
export default {
  name: 'App',
  data: () => ({
    version: ""
  }),
  async mounted() {
    this.version = (await this.axios.get('/api/version')).data
  }
};
</script>
