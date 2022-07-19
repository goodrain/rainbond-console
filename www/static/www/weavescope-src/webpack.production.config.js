const webpack = require('webpack');
const autoprefixer = require('autoprefixer');
const path = require('path');

const CleanWebpackPlugin = require('clean-webpack-plugin');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const GLOBALS = {
  'process.env': {NODE_ENV: '"production"'}
};

let PUBLIC_PATH = '';

if (process.env.EXTERNAL) {
  // Change this line to point to resources on an external host.
  PUBLIC_PATH = 'https://s3.amazonaws.com/static.weave.works/scope-ui/';
}

/**
 * This is the Webpack configuration file for production.
 */
module.exports = {

  // fail on first error when building release
  bail: true,

  cache: {},

  entry: {
    app: './app/scripts/main',
    // keep only some in here, to make vendors and app bundles roughly same size
    vendors: ['babel-polyfill', 'classnames', 'immutable',
      'react', 'react-dom', 'react-redux', 'redux', 'redux-thunk'
    ]
  },

  output: {
    path: path.join(__dirname, '../weavescope/'),
    filename: '[name]-[chunkhash].js',
    publicPath: PUBLIC_PATH
  },

  plugins: [
    new CleanWebpackPlugin(['build']),
    new webpack.DefinePlugin(GLOBALS),
    new webpack.optimize.CommonsChunkPlugin({ name: 'vendors', filename: 'vendors.js' }),
    new webpack.optimize.OccurrenceOrderPlugin(true),
    new webpack.IgnorePlugin(/^\.\/locale$/, /moment$/),
    new webpack.IgnorePlugin(/.*\.map$/, /xterm\/lib\/addons/),
    new ExtractTextPlugin('style-[name]-[chunkhash].css'),
    new HtmlWebpackPlugin({
      hash: true,
      chunks: ['vendors', 'app'],
      template: 'app/html/index.html',
      filename: 'index.html'
    }),
  ],

  module: {
    // Webpack is opionated about how pkgs should be laid out:
    // https://github.com/webpack/webpack/issues/1617
    noParse: [/xterm\/dist\/xterm\.js/],

    rules: [
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
        test: /\.ico$/,
        loader: 'file-loader',
        options: {
          name: '[name].[ext]'
        }
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
              minimize: true,
              includePaths: [
                path.resolve(__dirname, './node_modules/font-awesome'),
                path.resolve(__dirname, './node_modules/rc-slider'),
              ]
            }
          }]
        })
      }
    ]
  },

  resolve: {
    extensions: ['.js', '.jsx']
  },
};
