const webpack = require('webpack');
var path = require('path');
var htmlWebpackPlugin = require('html-webpack-plugin');
var cleanWebpackPlugin = require('clean-webpack-plugin');
var CommonsChunkPlugin = webpack.optimize.CommonsChunkPlugin;

module.exports = {
    entry: {
       'common' : ['./src/ui/widget', './src/utils/http','./src/utils/lang', './src/utils/util', './src/utils/page-controller', './src/utils/validationUtil', './src/comms/apiCenter','./src/comms/app-apiCenter', './src/comms/page-app-apiCenter', './src/comms/group-apiCenter', './src/comms/team-apiCenter' ],
       'home': ['./src/pages/home.js'],
       'user-pay' : ['./src/pages/user-pay.js'],
       'team': ['./src/pages/team.js'],
       'app-log': ['./src/pages/app-log.js'],
       'app-relation': ['./src/pages/app-relation.js'],
       'app-setting': ['./src/pages/app-setting.js'],
       'group-index': ['./src/pages/group-index.js'],
       'app-overview': ['./src/pages/app-overview.js'],
       'app-expansion': ['./src/pages/app-expansion.js'],
       'app-monitor': ['./src/pages/app-monitor.js'],
       'app-monitor-new': ['./src/pages/app-monitor-new.js'],
       'app-pay': ['./src/pages/app-pay.js'],
       'app-port': ['./src/pages/app-port.js'],
       'app-mnt': ['./src/pages/app-mnt.js'],
       'app-plugin': ['./src/pages/app-plugin.js'],
       'pay-renew': ['./src/pages/pay-renew.js']
    },
    output: {
        path: path.join(__dirname, "dists"),
        filename: '[name].js'
    },
    module:{
        rules:[
            {
                test: /\.html$/,
                use:[{
                    loader:'html-loader',
                    options:{
                       minimize: false,
                       interpolate: /\{\{.*?}}/
                    }
                }]
            },
            {
                test: /\.js$/,
                exclude: /node_modules|vendor/,
                loader: 'eslint-loader',
                enforce: 'pre'
            },
            {
                test:/\.js$/, 
                use:[{
                    loader:'babel-loader',
                    options:{
                       presets:['es2015', 'react', 'stage-0'],
                       plugins: [['import', {
                          libraryName: 'antd',
                          style: 'css'
                       }]]
                    }
                }]
            },{
                test:/\.css$/,
                use:[{
                    loader:'style-loader'
                },{
                    loader:'css-loader'
                }
                ]
            },{
                test:/\.(png|jpg|gif|woff|woff2|svg|eot|ttf)$/,
                use:[{
                    loader:'url-loader'
                }
                ]
            }
        ]
    },
    plugins:[
        new CommonsChunkPlugin({ name: 'common', filename: 'common.js' }),
        new cleanWebpackPlugin(['dists']),
        // new htmlWebpackPlugin({
        //     filename:'index.html',
        //     chunks:['vendors','app'],
        //     title: '好雨云帮管理后台',
        //     template:'./src/template/index.html'
        // }),
        new webpack.optimize.UglifyJsPlugin({
          sourceMap: false,
          mangle: false,
          compress: {
            warnings: false
          }
        }),
        new webpack.DefinePlugin({
          "process.env": { 
             NODE_ENV: JSON.stringify(process.env.NODE_ENV) 
           }
        })
        // new htmlWebpackPlugin({
        //  filename:'login.html',
        //  chunks:['login'],
        //  template:'./template/login.html'
        // })
    ],
    devServer:{
        //host: '172.16.0.125',
        port:9001,
        proxy:{
            '/backend/*':{
                target:'http://test.goodrain.com',
                changeOrigin: true,
                secure: false
            }
        }
    }
}