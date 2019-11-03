<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-app>
    <v-navigation-drawer v-model="drawer" app color="primary" dark width="200">
      <v-list dense>

        <div class="px-12 pt-1 pb-5">
          <router-link to="/">
            <v-img :src="require('./assets/logo-dark.svg')" contain width="100%"
                   class="center"/>
          </router-link>
        </div>

        <v-list-item-group v-model="item">
          <router-link :to="item.link" v-slot="href" v-for="(item, i) in menu" :key="i">
            <v-list-item link :href="href.href">
              <v-list-item-icon>
                <v-icon>{{ item.icon }}</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
          </router-link>
        </v-list-item-group>

      </v-list>
    </v-navigation-drawer>

    <v-app-bar app height="48">
      <v-app-bar-nav-icon @click.stop="drawer = !drawer"/>
      <v-spacer></v-spacer>
      v{{ version }}
      <v-btn text href="https://gen3.org/" target="_blank">
        <span class="mr-1">Website</span>
        <v-icon>mdi-open-in-new</v-icon>
      </v-btn>
    </v-app-bar>

    <v-content style="background-color: #eeeeee">
      <v-breadcrumbs :items="breadcrumb">
        <template v-slot:item="props">
          <router-link :to="props.item.href" v-slot="href">
            <v-breadcrumbs-item
                    :href="href.href"
                    :class="[props.item.disabled && 'disabled']"
            >
              {{ props.item.text }}
            </v-breadcrumbs-item>
          </router-link>
        </template>
      </v-breadcrumbs>

      <div class="px-5 pb-5">
        <router-view/>
      </div>
    </v-content>
  </v-app>
</template>

<style lang="scss">
  #app {
    font-family: 'Source Sans Pro', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
</style>

<script>
export default {
  name: 'App',
  data: () => ({
    menu: [
      {
        link: '/',
        icon: 'mdi-home',
        title: 'Home',
      },
      {
        link: '/docs',
        icon: 'mdi-code-tags',
        title: 'API Docs',
      },
    ],
    breadcrumb: [
      {
        text: 'Home',
        href: '/',
      },
      {
        text: 'API Docs',
        href: '/docs',
      },
    ],
    item: null,
    drawer: null,
    version: ""
  }),
  async mounted() {
    this.updateItem(this.$route)
    this.version = (await this.axios.get('/api/version')).data
  },

  watch: {
    '$route'(route) {
      this.updateItem(route)
    }
  },

  methods: {
    updateItem(route) {
      for (let i = 0; i < this.menu.length; i++) {
        if (route.path === this.menu[i].link) {
          this.item = i
          this.breadcrumb = [
            {
              text: 'Home',
              href: '/',
            },
          ]
          if (route.path !== '/') {
            this.breadcrumb.push(
              {
                text: this.menu[i].title,
                href: route.path,
              }
            )
          }
          break;
        }
      }
    }
  }
};
</script>
