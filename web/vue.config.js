module.exports = {
  devServer: {
    proxy: {
      '/api': {
        xfwd: true,
        target: 'http://localhost:8000'
      }
    }
  },
  "lintOnSave": false,
  "transpileDependencies": [
    "vuetify"
  ]
}