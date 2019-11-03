<template>
  <v-card>
    <HelloWorld msg="Welcome to Your Vue.js App"/>
  </v-card>
</template>

<script>
// @ is an alias to /src
import HelloWorld from '@/components/HelloWorld.vue'

export default {
  name: 'home',
  components: {
    HelloWorld
  }
}
</script>
