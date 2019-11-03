import Vue from 'vue';
import Vuetify from 'vuetify/lib';

Vue.use(Vuetify);

export default new Vuetify({
  theme: {
      options: {
        customProperties: true,
      },
    themes: {
      light: {
        primary: '#3283C8',
        accent: '#05B8EE',
        secondary: '#EF8523',
        accent2: '#FF9635',
        error: '#E74C3C',
        info: '#3283C8',
        success: '#7EC500',
        warning: '#F4B940'
      },
    },
  },
  icons: {
    iconfont: 'mdi',
  },
});
