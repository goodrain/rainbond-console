var path = require('path');

console.log(process.env.NODE_ENV)

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

    "env" : {
        "development": {
            "extraBabelPlugins": ["dva-hmr"],
            "html": {
                "template": "./src/index.ejs"
            },
            "publicPath": "/" ///
        },
        "production": {
            "html": {
                "filename": "../../templates/index.html", //
                "template": "./src/index.ejs"
            },
            "publicPath": "/static/dists", //
            "outputPath": path.resolve(__dirname, '../../dists')
        }
    },
    "ignoreMomentLocale" : true,
    "theme" : "./src/theme.js",
    "html" : {
        //"filename": "../../templates/index.html", //
        "template": "./src/index.ejs"
    },

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
