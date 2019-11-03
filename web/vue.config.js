module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000'
      }
    }
  },
  "lintOnSave": false,
  "transpileDependencies": [
    "vuetify"
  ]
}