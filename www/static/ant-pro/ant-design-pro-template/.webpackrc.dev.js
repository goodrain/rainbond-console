var path = require('path');
export default {
  "entry" : "src/index.js",
  "extraBabelPlugins" : [
    "transform-decorators-legacy",
    [
      "import", {
        "libraryName": "antd",
        "libraryDirectory": "es",
        "style": true
      }
    ]
  ],
  "outputPath" : path.resolve(__dirname, '../../dists'), //
  "env" : {
    "development": {
      "extraBabelPlugins": ["dva-hmr"]
    }
  },
  "ignoreMomentLocale" : true,
  "theme" : "./src/theme.js",
  "html" : {
    "filename": "../../templates/index.html", //
    "template": "./src/index.ejs"
  },
  "publicPath" : "/static/dists", //
  //"publicPath" : "/", ///
  "disableDynamicImport" : true,
  "hash" : true,
  "proxy" : {
    "/api": {
      "target": "http://5000.gra4b2e5.goodrain.ali-hz.goodrain.net:10080/",
      "changeOrigin": true,
      "pathRewrite": {
        "^/api": ""
      }
    }
  }
}
