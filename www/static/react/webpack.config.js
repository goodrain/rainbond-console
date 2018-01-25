const webpack = require('webpack');
var path = require('path');
var htmlWebpackPlugin = require('html-webpack-plugin');
var cleanWebpackPlugin = require('clean-webpack-plugin');


module.exports = {
    entry: {
       vendors: ['./src/libs/jquery.min', 'react', 'react-dom', 'react-redux', 'redux', 'redux-thunk', 'react-router-dom'],
       index: ['./src/index']
       
	},
    output: {
        publicPath:'/static/react/dists/', 
        path: path.join(__dirname, "dists"),
        //path: path.join(__dirname, ""),
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
        new webpack.optimize.CommonsChunkPlugin({ names: ['vendors', 'common'], minChunks: 2}),
        new cleanWebpackPlugin(['dists']),
    	new htmlWebpackPlugin({
            filename:'../../../templates/index.html',
            chunks:['common', 'vendors', 'index'],
            title: '好雨sso',
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
    }
}