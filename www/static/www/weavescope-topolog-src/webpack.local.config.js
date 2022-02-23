const webpack = require('webpack');
const autoprefixer = require('autoprefixer');
const path = require('path');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
/**
 * This is the Webpack configuration file for local development.
 * It contains local-specific configuration which includes:
 *
 * - Hot reloading configuration
 * - The entry points of the application
 * - Which loaders to use on what files to properly transpile the source
 *
 * For more information, see: http://webpack.github.io/docs/configuration.html
 */

module.exports = {
  // Efficiently evaluate modules with source maps
  devtool: 'eval-source-map',

  // Set entry points with hot loading
  entry: {
    app: [
      './app/scripts/main',
      'webpack-hot-middleware/client'
    ],
    'dev-app': [
      './app/scripts/main.dev',
      'webpack-hot-middleware/client'
    ],
    vendors: ['babel-polyfill', 'classnames', 'dagre', 'filesize', 'immutable',
      'moment', 'page', 'react', 'react-dom', 'react-motion', 'react-redux', 'redux',
      'redux-thunk', 'reqwest', 'xterm', 'webpack-hot-middleware/client'
    ]
  },

  // Used by Webpack Dev Middleware
  output: {
    publicPath: '',
    path: path.join(__dirname, 'build'),
    filename: '[name].js'
  },

  // Necessary plugins for hot load
  plugins: [
    new webpack.optimize.CommonsChunkPlugin({ name: 'vendors', filename: 'vendors.js' }),
    new webpack.optimize.OccurrenceOrderPlugin(),
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoEmitOnErrorsPlugin(),
    new webpack.IgnorePlugin(/^\.\/locale$/, /moment$/),
    new ExtractTextPlugin('style-[name]-[chunkhash].css'),
    new HtmlWebpackPlugin({
      chunks: ['vendors', 'dev-app'],
      template: 'app/html/index.html',
      filename: 'dev.html'
    }),
    new HtmlWebpackPlugin({
      chunks: ['vendors', 'app'],
      template: 'app/html/index.html',
      filename: 'index.html'
    }),
  ],

  // Transform source code using Babel and React Hot Loader
  module: {
    // Webpack is opionated about how pkgs should be laid out:
    // https://github.com/webpack/webpack/issues/1617
    noParse: [/xterm\/(.*).map$/, /xterm\/dist\/xterm\.js/],

    rules: [
      // {
      //   test: /\.js$/,
      //   exclude: /node_modules|vendor/,
      //   loader: 'eslint-loader',
      //   enforce: 'pre'
      // },
      {
        test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        loader: 'url-loader',
        options: {
          limit: 10000,
          minetype: 'application/font-woff',
        }
      },
      {
        test: /\.(ttf|eot|svg|ico)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        loader: 'file-loader'
      },
      {
        test: /\.jsx?$/,
        exclude: /node_modules|vendor/,
        loader: 'babel-loader'
      },
      {
        test: /\.(scss|css)$/,
        loader: ExtractTextPlugin.extract({
          fallback: 'style-loader',
          use: [{
            loader: 'css-loader'
          }, {
            loader: 'postcss-loader',
            options: {
              plugins: [
                autoprefixer({
                  browsers: ['last 2 versions']
                })
              ]
            }
          }, {
            loader: 'sass-loader',
            options: {
              includePaths: [
                path.resolve(__dirname, './node_modules/xterm'),
                path.resolve(__dirname, './node_modules/font-awesome'),
                path.resolve(__dirname, './node_modules/rc-slider'),
              ]
            }
          }],
        })
      }
    ]
  },

  // Automatically transform files with these extensions
  resolve: {
    extensions: ['.js', '.jsx']
  },
};
