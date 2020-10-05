const path = require('path');

module.exports = {
  entry: {
    main: './src/js/play_session.js',
    traces: './src/js/debug/traces.js',
  },
  devtool: 'eval-source-map',
  output: {
    path: path.resolve('./src/asobann/app/static'),
    filename: '[name].js',
  },
};
