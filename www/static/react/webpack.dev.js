const webpack = require('webpack');
var path = require('path');
var htmlWebpackPlugin = require('html-webpack-plugin');
var cleanWebpackPlugin = require('clean-webpack-plugin');


module.exports = {
    entry: {
       vendors: ['react', 'react-dom', 'react-redux', 'redux', 'redux-thunk'],
	   index: ['./src/index']
	},
    output: {
        path: path.join(__dirname, ""),
        filename: '[name].[chunkhash].js'
    },
    module:{
    	rules:[
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
        new webpack.optimize.CommonsChunkPlugin({ name: 'vendors', filename: 'vendors.js' }),
        new cleanWebpackPlugin(['dists']),
    	new htmlWebpackPlugin({
            filename:'index.html',
            chunks:['vendors', 'index'],
            title: '好雨SSO',
            template:'./src/template/index.html'
        }),
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
    ],
    devServer:{
    	port:9001
        // proxy:{
        //  '/proxy/*':{
        //      target:'http://5000.grd9b20c.goodrain.ali-sh.goodrain.net:10080/',
        //         changeOrigin: true,
        //         secure: false
        //  }
        // }
    }
}