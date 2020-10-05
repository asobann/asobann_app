const path = require('path');

module.exports = {
  entry: './src/js/play_session.js',
  devtool: 'eval-source-map',
  output: {
    path: path.resolve('./src/asobann/app/static'),
    filename: 'main.js',
  },
};
