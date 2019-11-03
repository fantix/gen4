<template>
  <v-container>
    <v-layout
      text-center
      wrap
    >
      <v-flex xs12>
        <v-img
          :src="require('../assets/logo.svg')"
          class="my-9"
          contain
          height="200"
        ></v-img>
      </v-flex>

      <v-flex mb-4>
        <h1 class="display-2 font-weight-bold mb-3 mt-5">
          Welcome to Gen3
        </h1>
        <p class="subheading font-weight-regular">
          This is a PoC project to build Gen3 on EdgeDB.
          <br>Source code is on
          <a href="https://github.com/fantix/gen4" target="_blank">GitHub</a>
        </p>
      </v-flex>

      <v-flex
        mb-5
        xs12
      >
        <h2 class="headline font-weight-bold mb-3">Powered by</h2>

        <v-layout justify-center>
          <a
            v-for="(next, i) in dependencies"
            :key="i"
            :href="next.href"
            class="subheading mx-3"
            target="_blank"
          >
            {{ next.text }}
          </a>
        </v-layout>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<script>
export default {
  data: () => ({
    dependencies: [
      {
        text: 'EdgeDB',
        href: 'https://edgedb.com/',
      },
      {
        text: 'FastAPI',
        href: 'https://fastapi.tiangolo.com/',
      },
      {
        text: 'Poetry',
        href: 'https://poetry.eustace.io/',
      },
      {
        text: 'Vuetify',
        href: 'https://vuetifyjs.com/',
      },
    ],
  }),
};
</script>
